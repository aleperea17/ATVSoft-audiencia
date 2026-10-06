"""Aviso diario si el token de Instagram está por vencer o ya no sirve."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from decouple import config

from src.graph_errors import GraphAPIError
from src.services.graph_client import request_json
from src.services.instagram_service import credentials, graph_version

logger = logging.getLogger("audiencia.token")

_WARN_WITHIN = 10 * 24 * 60 * 60


def _expires_soon(unix_ts: int | None, *, ignore_zero: bool) -> tuple[bool, str]:
    if unix_ts is None:
        return False, "ausente"
    if ignore_zero and unix_ts == 0:
        return False, "sin vencimiento"
    moment = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    label = moment.strftime("%Y-%m-%d %H:%M UTC")
    remaining = unix_ts - int(datetime.now(timezone.utc).timestamp())
    return remaining < _WARN_WITHIN, label


async def check_instagram_token() -> None:
    try:
        await asyncio.to_thread(_check_sync)
    except Exception:
        logger.exception("no se pudo revisar el token de Instagram")


def _check_sync() -> None:
    creds = credentials()
    if creds is None:
        _alert("Faltan IG_ACCESS_TOKEN o IG_USER_ID. No se pudo revisar el token.")
        return
    token, _ig_user_id = creds
    version = graph_version()
    url = (
        f"https://graph.facebook.com/{quote(version)}/debug_token"
        f"?input_token={quote(token)}&access_token={quote(token)}"
    )
    try:
        payload = request_json(url, attempts=1)
    except GraphAPIError as exc:
        _alert(f"El token de Instagram no se pudo validar (HTTP {exc.http_status}).")
        return

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or data.get("is_valid") is not True:
        _alert("El token de Instagram es inválido.")
        return

    reasons = []
    expires_at = data.get("expires_at")
    data_access = data.get("data_access_expires_at")
    token_soon, token_label = _expires_soon(expires_at if isinstance(expires_at, int) else None, ignore_zero=True)
    access_soon, access_label = _expires_soon(data_access if isinstance(data_access, int) else None, ignore_zero=False)
    if token_soon:
        reasons.append(f"expires_at {token_label}")
    if access_soon:
        reasons.append(f"data_access_expires_at {access_label}")
    if not reasons:
        logger.info(
            "token de Instagram vigente (expires_at=%s, data_access_expires_at=%s)",
            token_label,
            access_label,
        )
        return
    _alert("El token de Instagram vence en menos de 10 días: " + "; ".join(reasons) + ".")


def _alert(message: str) -> None:
    logger.warning(message)
    hook = (config("DISCORD_WEBHOOK_URL", default="") or "").strip()
    if not hook:
        return
    body = json.dumps({"content": "ATV Audiencia: " + message}).encode("utf-8")
    import ssl
    import urllib.error
    import urllib.request

    import certifi

    req = urllib.request.Request(
        hook,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "atv-audiencia"},
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        logger.warning("Discord rechazó el aviso de token (HTTP %s)", exc.code)
    except OSError as exc:
        logger.warning("no se pudo avisar a Discord: %s", type(exc).__name__)
