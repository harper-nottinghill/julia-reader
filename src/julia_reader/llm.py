"""OpenAI-compatible chat completion — one HTTP POST, stdlib only."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Callable


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def chat_completion(
    *,
    system: str,
    user: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout_s: int = 600,
) -> str:
    """POST to ``{base}/chat/completions``. Returns assistant message content (plain text)."""
    key = api_key or _env("JULIA_READER_API_KEY") or _env("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No API key: set JULIA_READER_API_KEY or OPENAI_API_KEY in the environment."
        )
    base = (base_url or _env("JULIA_READER_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
    mid = model or _env("JULIA_READER_MODEL", "gpt-4o-mini")
    url = f"{base}/chat/completions"
    extra = _env("JULIA_READER_EXTRA_HEADERS")  # optional JSON object string
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    if extra:
        try:
            for k, v in json.loads(extra).items():
                headers[str(k)] = str(v)
        except json.JSONDecodeError as exc:
            raise RuntimeError("JULIA_READER_EXTRA_HEADERS must be valid JSON object") from exc

    payload: dict[str, Any] = {
        "model": mid,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.25,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM response missing choices: {str(body)[:500]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"LLM response missing string content: {str(choices[0])[:500]}")
    return content


def make_completer_for(
    model: str | None,
    base_url: str | None = None,
) -> tuple[str, str, Callable[[str, str], str]]:
    """Build (model_id, base_url, completer). Empty *model* falls back to env."""
    base = (base_url or _env("JULIA_READER_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
    mid = (model or _env("JULIA_READER_MODEL", "gpt-4o-mini")).strip() or "gpt-4o-mini"

    def complete(system: str, user: str) -> str:
        return chat_completion(system=system, user=user, model=mid, base_url=base)

    return mid, base, complete


def make_completer() -> tuple[str, str, Callable[[str, str], str]]:
    """Environment defaults."""
    return make_completer_for(None, None)
