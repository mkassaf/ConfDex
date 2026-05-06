from __future__ import annotations

import json
import logging
import os
import re

import litellm

logger = logging.getLogger(__name__)

# Silence litellm's verbose success logs
litellm.success_callback = []
litellm.set_verbose = False

# Default model — overridden via --model flag or LLM_MODEL env var
DEFAULT_MODEL = "claude-sonnet-4-6"

_PAPER_LIST_PROMPT = """\
You are given the full HTML of a conference program or workshop page.
Extract every accepted paper you can find. For each paper return a JSON object with:
  - "title": string
  - "abstract": string or null
  - "detail_url": absolute URL to the paper detail page, or null if not present

Return ONLY a JSON array of these objects, no prose, no markdown fences.
If you find no papers, return an empty array [].

Base URL for resolving relative links: {base_url}
"""

_ABSTRACT_PROMPT = """\
You are given the full HTML of a single conference paper detail page.
Extract the abstract text exactly as written. Return ONLY the abstract as plain text.
If there is no abstract, return the single word: null
"""


def _resolve_api_key(model: str, api_key: str | None) -> str | None:
    """
    Return the api_key to use. Priority:
      1. Explicit --api-key parameter
      2. Provider-specific env var (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
      3. Generic LITELLM_API_KEY env var
    Ollama and other local models need no key — return None silently.
    """
    if api_key:
        return api_key

    local_prefixes = ("ollama/", "ollama_chat/", "huggingface/", "llamacpp/")
    if any(model.startswith(p) for p in local_prefixes):
        return None  # local model, no key needed

    # Try well-known env vars by provider prefix
    provider_env: dict[str, str] = {
        "claude": "ANTHROPIC_API_KEY",
        "anthropic/": "ANTHROPIC_API_KEY",
        "gpt": "OPENAI_API_KEY",
        "openai/": "OPENAI_API_KEY",
        "gemini/": "GEMINI_API_KEY",
        "groq/": "GROQ_API_KEY",
        "mistral/": "MISTRAL_API_KEY",
        "cohere/": "COHERE_API_KEY",
    }
    for prefix, env_var in provider_env.items():
        if model.startswith(prefix):
            key = os.environ.get(env_var)
            if key:
                return key
            logger.warning("No API key for model %r — set %s or pass --api-key", model, env_var)
            return None

    return os.environ.get("LITELLM_API_KEY")


def _call(model: str, api_key: str | None, prompt: str, max_tokens: int = 8192) -> str:
    key = _resolve_api_key(model, api_key)
    kwargs: dict = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    if key:
        kwargs["api_key"] = key
    response = litellm.completion(**kwargs)
    return response.choices[0].message.content.strip()


def extract_papers_from_html(html: str, base_url: str, model: str, api_key: str | None) -> list[dict]:
    """Use an LLM to extract paper list (title, abstract, detail_url) from arbitrary HTML."""
    logger.info("Using LLM (%s) to extract paper list from %s", model, base_url)
    prompt = _PAPER_LIST_PROMPT.format(base_url=base_url) + "\n\n<html>\n" + html[:150_000] + "\n</html>"
    raw = _call(model, api_key, prompt, max_tokens=8192)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        logger.warning("LLM returned non-JSON: %s", raw[:200])
        return []


def extract_abstract_from_html(html: str, model: str, api_key: str | None) -> str | None:
    """Use an LLM to extract the abstract when CSS selectors fail."""
    logger.info("Using LLM (%s) to extract abstract", model)
    prompt = _ABSTRACT_PROMPT + "\n\n<html>\n" + html[:80_000] + "\n</html>"
    result = _call(model, api_key, prompt, max_tokens=1024)
    return None if result.lower() == "null" else result
