from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Callable

import litellm

from confscraper.models import Paper

logger = logging.getLogger(__name__)

litellm.success_callback = []
litellm.failure_callback = []
litellm.set_verbose = False
litellm.suppress_debug_info = True

# ── Stage 1: structured summary ─────────────────────────────────────────────

_SUMMARIZE_PROMPT_V2 = """\
Analyze this conference paper carefully. Return a JSON object with exactly these keys:

  "summary"    : 2-3 sentence summary structured as: (1) the problem/challenge addressed,
                 (2) the proposed approach or method, (3) the key result or contribution.
  "keywords"   : list of 5-7 specific technical terms that domain experts would use to find
                 this paper (prefer precise technical phrases over generic words).
  "methodology": exactly one of: "empirical study", "systematic review", "tool or framework",
                 "formal methods", "machine learning", "user study", "survey", "other"
  "domain"     : primary research domain in 3-5 words (e.g. "program analysis",
                 "human-computer interaction", "distributed systems")

Return ONLY valid JSON, no markdown fences, no prose.

Title: {title}
Abstract: {abstract}
"""

# ── Stage 2: topic relevance scoring ────────────────────────────────────────

_TOPIC_SCORE_PROMPT_V2 = """\
You are evaluating whether a research paper is PRIMARILY about the given topic.
Be strict and conservative: a high score means the topic is the paper's central subject,
not merely a tool, backdrop, or side contribution.

Topic of Interest: "{topic}"

Paper Information:
  Title:       {title}
  Summary:     {summary}
  Keywords:    {keywords}
  Domain:      {domain}
  Methodology: {methodology}

First ask yourself: "Would this paper be fundamentally different if the topic did not exist?"
  - YES → the topic is its primary focus → score 7-10
  - PARTIALLY → the topic is one of several themes → score 4-6
  - NO  → the topic is peripheral, a tool, or background → score 0-3

Strict scoring scale:
  9-10  The paper's core contribution IS the topic. The title/abstract make this unmistakable.
  7-8   The topic is a primary focus. Removing it would make the paper's main claim collapse.
  5-6   The topic is one of 2-3 equal themes, or a direct application domain.
  3-4   The topic appears but is background, motivation, or a minor component only.
  1-2   The topic is briefly mentioned or loosely related at best.
  0     The topic is absent or the connection is a stretch.

Important rules:
  - Papers that USE the topic as a tool/baseline without studying it → score ≤ 3
  - Papers that MENTION the topic in related work only → score ≤ 2
  - Papers with the topic in a single example or case study → score ≤ 4
  - Do NOT give 7+ unless the topic is central to the research question and contribution

Return a JSON object with exactly these keys:
  "score"    : integer 0-10
  "reasoning": 1-2 sentences explaining why the topic is or is not the primary focus
  "matching" : list of specific aspects where the paper directly addresses the topic (empty if score < 4)

Return ONLY valid JSON, no markdown fences.
"""

# ── Legacy single-stage prompts (kept for backward compat) ──────────────────

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


def _call_llm(prompt: str, model: str, api_key: str | None, max_tokens: int = 1024) -> dict:
    kwargs: dict = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        timeout=60,
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


def categorize_paper_v2(
    paper: Paper,
    model: str,
    api_key: str | None,
    topic: str | None = None,
) -> dict:
    """
    Two-stage pipeline:
      Stage 1 — structured summary (summary, keywords, methodology, domain)
      Stage 2 — topic relevance score + reasoning (only when topic given)

    Returns a dict with: title, source_url, doi, summary, keywords,
    methodology, domain, and (when topic given) score, score_reasoning, score_matching.
    """
    base: dict = {"title": paper.title, "source_url": paper.source_url, "doi": paper.doi}
    if topic is not None:
        base["score"] = None
        base["score_reasoning"] = None
        base["score_matching"] = []

    if not paper.abstract:
        return {
            **base,
            "summary": None,
            "keywords": [],
            "methodology": None,
            "domain": None,
        }

    # Stage 1: structured summarization
    prompt1 = _SUMMARIZE_PROMPT_V2.format(title=paper.title, abstract=paper.abstract)
    try:
        stage1 = _call_llm(prompt1, model, api_key, max_tokens=1024)
    except Exception as e:
        logger.error("Stage-1 LLM call failed for '%s': %s", paper.title[:60], e)
        return {
            **base,
            "summary": None,
            "keywords": [],
            "methodology": None,
            "domain": None,
        }

    summary = stage1.get("summary")
    keywords = stage1.get("keywords", [])
    methodology = stage1.get("methodology")
    domain = stage1.get("domain")

    result = {
        "title": paper.title,
        "source_url": paper.source_url,
        "doi": paper.doi,
        "summary": summary,
        "keywords": keywords,
        "methodology": methodology,
        "domain": domain,
    }

    # Stage 2: topic relevance scoring (separate focused call)
    if topic is not None:
        result["score"] = None
        result["score_reasoning"] = None
        result["score_matching"] = []

        if summary:
            prompt2 = _TOPIC_SCORE_PROMPT_V2.format(
                topic=topic,
                title=paper.title,
                summary=summary,
                keywords=", ".join(keywords) if keywords else "none",
                domain=domain or "unknown",
                methodology=methodology or "unknown",
            )
            try:
                stage2 = _call_llm(prompt2, model, api_key, max_tokens=512)
                raw_score = stage2.get("score")
                if raw_score is not None:
                    raw_score = max(0, min(10, int(raw_score)))
                result["score"] = raw_score
                result["score_reasoning"] = stage2.get("reasoning")
                result["score_matching"] = stage2.get("matching", [])
            except Exception as e:
                logger.error("Stage-2 LLM call failed for '%s': %s", paper.title[:60], e)

    return result


def categorize_paper(
    paper: Paper,
    model: str,
    api_key: str | None,
    topic: str | None = None,
) -> dict:
    """
    Backward-compatible wrapper around categorize_paper_v2.
    Returns the same shape as the old function (title, source_url, doi,
    summary, keywords, score) with the new fields also present.
    """
    return categorize_paper_v2(paper, model, api_key, topic)


async def categorize_papers(
    papers: list[Paper],
    model: str,
    api_key: str | None,
    topic: str | None = None,
    concurrency: int = 5,
    progress_cb: Callable[[], None] | None = None,
) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(paper: Paper) -> dict:
        async with sem:
            result = await asyncio.to_thread(categorize_paper_v2, paper, model, api_key, topic)
            if progress_cb is not None:
                progress_cb()
            return result

    return await asyncio.gather(*(_one(p) for p in papers))
