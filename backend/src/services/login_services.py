"""Login propio. No emite ecosystem_session."""

from __future__ import annotations

import hashlib
import hmac
import time

import bcrypt
from decouple import config
from fastapi import HTTPException, Request, status

from src.auth import SESSION_MAX_AGE, audiencia_secret, sign_session

_WINDOW_SECONDS = 15 * 60
_MAX_FAILURES = 5
_failures: dict[str, list[float]] = {}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [item.strip() for item in forwarded.split(",") if item.strip()]
    if parts:
        return parts[-1]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _recent(ip: str, now: float) -> list[float]:
    return [moment for moment in _failures.get(ip, []) if now - moment < _WINDOW_SECONDS]


def is_rate_limited(ip: str, now: float | None = None) -> bool:
    moment = time.time() if now is None else now
    hits = _recent(ip, moment)
    _failures[ip] = hits
    return len(hits) >= _MAX_FAILURES


def record_failure(ip: str, now: float | None = None) -> None:
    moment = time.time() if now is None else now
    hits = _recent(ip, moment)
    hits.append(moment)
    _failures[ip] = hits


def clear_failures(ip: str) -> None:
    _failures.pop(ip, None)


def _password_ok(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str, ip: str) -> str:
    if is_rate_limited(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Probá de nuevo en unos minutos.",
        )
    expected_user = (config("AUDIENCIA_ADMIN_USER", default="") or "").strip()
    password_hash = (config("AUDIENCIA_ADMIN_PASSWORD_HASH", default="") or "").strip()
    secret = audiencia_secret()
    if not expected_user or not password_hash or len(secret) < 32:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Login no configurado")

    given = hashlib.sha256(username.strip().encode("utf-8")).digest()
    wanted = hashlib.sha256(expected_user.encode("utf-8")).digest()
    user_ok = hmac.compare_digest(given, wanted)
    password_ok = _password_ok(password, password_hash)
    if not (user_ok and password_ok):
        record_failure(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")

    clear_failures(ip)
    return sign_session({"sub": expected_user, "exp": int(time.time()) + SESSION_MAX_AGE}, secret)
