"""OpenAI-compatible chat completion — one HTTP POST, stdlib only.

Includes retry with exponential backoff for transient API failures
(rate limits, timeouts, 5xx server errors).  Retry behaviour is
configured in ``reader_config.py`` and can be overridden via env vars.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .reader_config import LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY

logger = logging.getLogger("julia_reader.llm_retry")

# HTTP status codes that indicate a transient server-side problem.
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}

# HTTP status codes that are *never* retried (client errors).
_NON_RETRYABLE_STATUS_CODES = {400, 401, 403}


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _is_retryable_http_error(exc: urllib.error.HTTPError) -> bool:
    """Return True if *exc* represents a transient HTTP error worth retrying."""
    if exc.code in _TRANSIENT_STATUS_CODES:
        return True
    if exc.code in _NON_RETRYABLE_STATUS_CODES:
        return False
    # Other status codes (e.g. 404, 405) — don't retry by default.
    return False


def _is_retryable_error(exc: BaseException) -> bool:
    """Classify an exception as retryable (transient) or not."""
    # urllib HTTP errors — check status code.
    if isinstance(exc, urllib.error.HTTPError):
        return _is_retryable_http_error(exc)
    # URL errors wrapping transient problems (timeouts, connection resets).
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (socket.timeout, TimeoutError, ConnectionError, OSError)):
            return True
        msg = str(reason).lower()
        transient_signals = ("timeout", "timed out", "connection", "reset", "refused", "overloaded", "capacity")
        return any(s in msg for s in transient_signals)
    # Bare socket / timeout errors.
    if isinstance(exc, (socket.timeout, TimeoutError, ConnectionError)):
        return True
    # RuntimeError wrapping an HTTP error (re-raised by our own code during
    # an earlier attempt) — check the message for transient signals.
    if isinstance(exc, RuntimeError):
        msg = str(exc).lower()
        for code in _TRANSIENT_STATUS_CODES:
            if f"http {code}" in msg:
                return True
        transient_signals = ("rate limit", "timeout", "timed out", "connection", "overloaded", "capacity", "server error")
        return any(s in msg for s in transient_signals)
    return False


def _do_http_request(
    *,
    url: str,
    data: bytes,
    headers: dict[str, str],
    timeout_s: int,
    ctx: ssl.SSLContext,
) -> dict[str, Any]:
    """Execute a single HTTP POST and return the parsed JSON body.

    Raises the original ``urllib.error.HTTPError`` (or ``URLError``,
    ``socket.timeout``) so the caller can classify and retry.
    """
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat_completion(
    *,
    system: str,
    user: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout_s: int = 600,
    # Allow callers (e.g. tests) to override retry settings.
    _max_retries: int | None = None,
    _base_delay: float | None = None,
) -> str:
    """POST to ``{base}/chat/completions``. Returns assistant message content (plain text).

    Retries transient failures (429, 5xx, timeouts) with exponential
    backoff.  Non-retryable errors (401, 403, 400) raise immediately.
    """
    max_retries = _max_retries if _max_retries is not None else LLM_MAX_RETRIES
    base_delay = _base_delay if _base_delay is not None else LLM_RETRY_BASE_DELAY

    key = api_key or _env("JULIA_READER_API_KEY") or _env("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No API key: set JULIA_READER_API_KEY or OPENAI_API_KEY in the environment."
        )
    base = (base_url or _env("JULIA_READER_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
    mid = model or _env("JULIA_READER_MODEL", "gpt-4o-mini")
    url = f"{base}/chat/completions"
    extra = _env("JULIA_READER_EXTRA_HEADERS")  # optional JSON object string
    headers: dict[str, str] = {
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
    ctx = ssl.create_default_context()

    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            body = _do_http_request(
                url=url, data=data, headers=headers, timeout_s=timeout_s, ctx=ctx,
            )
        except Exception as exc:
            last_exc = exc

            # Non-retryable → log and re-raise immediately.
            if not _is_retryable_error(exc):
                logger.error(
                    "LLM call failed with non-retryable error (attempt %d): %s",
                    attempt + 1, exc,
                )
                if isinstance(exc, urllib.error.HTTPError):
                    detail = exc.read().decode("utf-8", errors="replace")[:2000]
                    raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
                raise

            # Retryable but out of retries → log final failure and raise.
            if attempt >= max_retries:
                logger.error(
                    "LLM call failed after %d attempts (no more retries). Last error: %s",
                    max_retries + 1, exc,
                )
                if isinstance(exc, urllib.error.HTTPError):
                    detail = exc.read().decode("utf-8", errors="replace")[:2000]
                    raise RuntimeError(
                        f"LLM HTTP {exc.code} (retried {max_retries}x): {detail}"
                    ) from exc
                raise RuntimeError(
                    f"LLM call failed after {max_retries + 1} attempts: {exc}"
                ) from exc

            # Retryable with retries remaining → log, back off, retry.
            delay = base_delay * (2 ** attempt)
            status = getattr(exc, "code", None) or ""
            logger.warning(
                "LLM call hit transient error (attempt %d/%d, status=%s). "
                "Retrying in %.1fs: %s",
                attempt + 1, max_retries + 1, status, delay, exc,
            )
            time.sleep(delay)
            continue

        # --- Successful HTTP response — validate body ---
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError(f"LLM response missing choices: {str(body)[:500]}")
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"LLM response missing string content: {str(choices[0])[:500]}")
        return content

    # Should be unreachable, but just in case.
    raise last_exc  # type: ignore[misc]


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
