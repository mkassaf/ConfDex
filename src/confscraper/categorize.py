from __future__ import annotations

import asyncio
import json
import logging
import re

import litellm

from confscraper.models import Paper

logger = logging.getLogger(__name__)

litellm.success_callback = []
litellm.failure_callback = []
litellm.set_verbose = False
litellm.suppress_debug_info = True

_SUMMARIZE_PROMPT = """\
Given this paper title and abstract, return a JSON object with exactly these keys:
  "summary"  : 2-3 sentence plain-English summary of what the paper does and its main result.
  "keywords" : list of 5 keywords or short phrases that best describe the paper's topics.

Return ONLY the JSON object, no markdown fences, no prose.

Title: {title}
Abstract: {abstract}
"""

_SUMMARIZE_WITH_TOPIC_PROMPT = """\
Given this paper title and abstract, return a JSON object with exactly these keys:
  "summary"  : 2-3 sentence plain-English summary of what the paper does and its main result.
  "keywords" : list of 5 keywords or short phrases that best describe the paper's topics.
  "score"    : integer 0-10 indicating how relevant this paper is to the topic "{topic}".
               0 = completely unrelated, 10 = directly addresses the topic.

Return ONLY the JSON object, no markdown fences, no prose.

Title: {title}
Abstract: {abstract}
"""


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise ValueError(f"LLM returned non-JSON: {raw[:200]}")


def _call_llm(prompt: str, model: str, api_key: str | None) -> dict:
    kwargs: dict = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    if api_key:
        kwargs["api_key"] = api_key
    response = litellm.completion(**kwargs)
    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


def validate_model(model: str, api_key: str | None) -> None:
    """
    Fire a minimal test call to catch bad model names, missing keys, or
    Ollama models that haven't been pulled — before processing all papers.
    Raises with a clear message on failure.
    """
    kwargs: dict = dict(
        model=model,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=1,
    )
    if api_key:
        kwargs["api_key"] = api_key
    try:
        litellm.completion(**kwargs)
    except Exception as e:
        _raise_helpful(model, e)


def _raise_helpful(model: str, original: Exception) -> None:
    msg = str(original)
    msg_lower = msg.lower()
    model_name = model.split("/", 1)[-1]
    hint = ""

    if "failed to load" in msg_lower or "resource limit" in msg_lower:
        hint = (
            f"\n  The model loaded but ran out of memory or hit a resource limit."
            f"\n  Try a smaller model:  ollama pull qwen3:4b  (or llama3.2, phi3, gemma2:2b)"
            f"\n  Or free RAM and restart Ollama: ollama stop && ollama serve"
        )
    elif "not found" in msg_lower and "ollama" in model.lower():
        hint = f"\n  Run: ollama pull {model_name}"
    elif "not found" in msg_lower or "404" in msg:
        hint = "\n  Check the model name is correct."
    elif "connection" in msg_lower and "ollama" in model.lower():
        hint = "\n  Ollama does not appear to be running.  Start it with: ollama serve"
    elif "api key" in msg_lower or "unauthorized" in msg_lower or "401" in msg:
        hint = "\n  Pass --api-key or set the provider env var (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)."

    raise RuntimeError(
        f"LLM model check failed for '{model}': {original}{hint}"
    ) from original


def categorize_paper(
    paper: Paper,
    model: str,
    api_key: str | None,
    topic: str | None = None,
) -> dict:
    """
    Returns a dict: title, summary, keywords, and (if topic given) score.
    Returns nulls if the paper has no abstract or if the LLM call fails.
    """
    base: dict = {"title": paper.title}
    if topic is not None:
        base["score"] = None

    if not paper.abstract:
        return {**base, "summary": None, "keywords": []}

    if topic:
        prompt = _SUMMARIZE_WITH_TOPIC_PROMPT.format(
            title=paper.title, abstract=paper.abstract, topic=topic
        )
    else:
        prompt = _SUMMARIZE_PROMPT.format(title=paper.title, abstract=paper.abstract)

    try:
        data = _call_llm(prompt, model, api_key)
    except Exception as e:
        logger.error("LLM call failed for '%s': %s", paper.title[:60], e)
        return {**base, "summary": None, "keywords": []}

    result = {
        "title": paper.title,
        "summary": data.get("summary"),
        "keywords": data.get("keywords", []),
    }
    if topic is not None:
        result["score"] = data.get("score")
    return result


async def categorize_papers(
    papers: list[Paper],
    model: str,
    api_key: str | None,
    topic: str | None = None,
    concurrency: int = 5,
) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(paper: Paper) -> dict:
        async with sem:
            return await asyncio.to_thread(categorize_paper, paper, model, api_key, topic)

    return await asyncio.gather(*(_one(p) for p in papers))
