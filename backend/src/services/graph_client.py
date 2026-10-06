"""HTTP sync a Graph API. Llamar siempre desde asyncio.to_thread."""

from __future__ import annotations

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request

import certifi

from src.graph_errors import GraphAPIError, GraphRateLimitError, is_rate_limit

logger = logging.getLogger("audiencia.graph")

_TOKEN_RE = re.compile(r"access_token=[^&\s]+", re.IGNORECASE)


def redact(text: str) -> str:
    return _TOKEN_RE.sub("access_token=REDACTED", text or "")


def _parse_error(http_status: int, raw: str) -> GraphAPIError:
    code = None
    message = raw[:400]
    try:
        payload = json.loads(raw) if raw else {}
        err = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(err, dict):
            code = err.get("code")
            if isinstance(code, str) and code.isdigit():
                code = int(code)
            message = str(err.get("message") or message)
    except json.JSONDecodeError:
        pass
    if is_rate_limit(http_status, code if isinstance(code, int) else None):
        return GraphRateLimitError(message, http_status=http_status, code=code if isinstance(code, int) else None)
    return GraphAPIError(message, http_status=http_status, code=code if isinstance(code, int) else None)


def request_json(url: str, *, timeout: int = 45, attempts: int = 4) -> dict:
    delay = 2.0
    last: GraphRateLimitError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _request_once(url, timeout=timeout)
        except GraphRateLimitError as exc:
            last = exc
            logger.warning(
                "rate limit Graph (código %s) intento %s/%s; esperando %.0fs",
                exc.code,
                attempt,
                attempts,
                delay,
            )
            if attempt == attempts:
                break
            time.sleep(delay)
            delay = min(delay * 2, 60)
    assert last is not None
    raise last


def _request_once(url: str, *, timeout: int) -> dict:
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raw = ""
        err = _parse_error(exc.code, raw)
        logger.info("graph HTTP %s: %s", exc.code, redact(str(err))[:300])
        raise err from exc
    except GraphAPIError:
        raise
    except Exception as exc:
        raise GraphAPIError(f"error de red: {exc}") from exc
