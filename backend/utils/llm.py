"""
LLM helper utilities

Uses OpenAI to generate a short summary and key topics from cleaned OCR text.

Environment:
  - OPENAI_API_KEY must be set in the environment for production use.

This module provides a synchronous helper `summarize_text` which returns a
dictionary: {"summary": str, "key_topics": List[str]}.
"""
from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List

try:
    import openai
except Exception:
    openai = None  # will raise later if used without dependency

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def _parse_json_from_text(text: str) -> Dict[str, Any]:
    """Try to extract a JSON object from the model response text."""
    try:
        return json.loads(text)
    except Exception:
        # Fallback: try to find first {...} block
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    # Last fallback: return best-effort plain text as summary
    return {"summary": text.strip(), "key_topics": []}


def summarize_text(text: str) -> Dict[str, Any]:
    """Call OpenAI to summarize text and return {'summary', 'key_topics'}.

    This is a synchronous helper intended to be run in a background thread
    (e.g. via asyncio.to_thread or FastAPI BackgroundTasks).
    """
    if not text or not text.strip():
        return {"summary": "", "key_topics": []}

    if openai is None:
        raise RuntimeError("openai package is not installed. Add 'openai' to requirements.txt")

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    openai.api_key = OPENAI_API_KEY

    instruction = (
        "You are a concise summarization assistant.\n"
        "Given the cleaned text of an academic or technical document, produce a JSON object with two fields:\n"
        "1) summary: a 1-2 sentence human-readable summary of the document.\n"
        "2) key_topics: an array of 5-8 short topic phrases (3-6 words each) capturing the main topics or concepts.\n"
        "Return only valid JSON and no additional commentary.\n"
        "If uncertain, provide best-effort answers.\n"
    )

    prompt = f"{instruction}\n\nDocument:\n{text}\n"

    try:
        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=400,
        )

        content = response["choices"][0]["message"]["content"]

        parsed = _parse_json_from_text(content)

        # Normalize fields
        summary = parsed.get("summary", "") if isinstance(parsed, dict) else ""
        key_topics = parsed.get("key_topics", []) if isinstance(parsed, dict) else []

        # Ensure key_topics is a list of strings
        if not isinstance(key_topics, list):
            key_topics = []
        else:
            key_topics = [str(k).strip() for k in key_topics if str(k).strip()]

        return {"summary": str(summary).strip(), "key_topics": key_topics}

    except Exception as e:
        # Bubble up a reasonable error for the caller to handle/log
        raise RuntimeError(f"LLM summarization failed: {e}")
