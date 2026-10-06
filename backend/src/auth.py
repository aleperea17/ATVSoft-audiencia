"""Cookie compartida ecosystem_session, verificada en local con HMAC-SHA256.

Formato (lo emite el login del ecosistema, este módulo solo verifica):

    ecosystem_session = <payload_b64>.<sig_b64>

- payload_b64: JSON UTF-8 en base64 url-safe, sin padding.
- sig_b64: HMAC-SHA256 de los bytes de payload_b64 (el segmento tal como viaja),
  clave ECOSYSTEM_SESSION_SECRET, base64 url-safe sin padding.
- El JSON debe incluir "exp" (unix UTC, segundos). "sub" es opcional.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from decouple import config
from fastapi import HTTPException, Request, status

COOKIE_NAME = "ecosystem_session"
_SKEW_SECONDS = 60


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def sign_session(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64encode(body)
    digest = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return payload_b64 + "." + _b64encode(digest)


def verify_session_token(token: str, secret: str, now: float | None = None) -> dict[str, Any]:
    if not secret or len(secret) < 32:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no disponible")
    if not token or "." not in token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    payload_b64, sig_b64 = token.split(".", 1)
    if not payload_b64 or not sig_b64 or "." in sig_b64:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    expected = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        given = _b64decode(sig_b64)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida") from exc
    if not hmac.compare_digest(expected, given):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    try:
        payload = json.loads(_b64decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    current = time.time() if now is None else now
    if float(exp) + _SKEW_SECONDS < current:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión vencida")
    return payload


def session_secret() -> str:
    return (config("ECOSYSTEM_SESSION_SECRET", default="") or "").strip()


def require_session(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME, "")
    return verify_session_token(token, session_secret())
