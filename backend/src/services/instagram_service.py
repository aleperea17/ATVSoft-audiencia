"""Lectura de reels, comentarios y Business Discovery. Sin Pony."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote

from decouple import config

from src.graph_errors import GraphAPIError
from src.services.graph_client import request_json

logger = logging.getLogger("audiencia.instagram")

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_DISCOVERY_FIELDS = "biography,website,followers_count,media.limit(8){caption}"


def graph_version() -> str:
    raw = (config("IG_GRAPH_VERSION", default="v25.0") or "v25.0").strip()
    if not re.fullmatch(r"v\d+\.\d+", raw):
        return "v25.0"
    return raw


def credentials() -> tuple[str, str] | None:
    token = (config("IG_ACCESS_TOKEN", default="") or "").strip()
    ig_user_id = (config("IG_USER_ID", default="") or "").strip()
    if not token or not ig_user_id:
        return None
    return token, ig_user_id


def _base() -> str:
    return f"https://graph.facebook.com/{graph_version()}"


def _parse_timestamp(raw: str) -> datetime | None:
    text = (raw or "").strip().replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", text) and not re.search(r"[+-]\d{2}:\d{2}$", text):
        text = text[:-2] + ":" + text[-2:]
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def fetch_reel_page(url: str | None = None) -> dict:
    """Una página de media. El caller pagina y corta por rate limit."""
    creds = credentials()
    if creds is None:
        raise GraphAPIError("faltan IG_ACCESS_TOKEN o IG_USER_ID")
    token, ig_user_id = creds
    if url is None:
        fields = "id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp"
        url = (
            f"{_base()}/{quote(ig_user_id)}/media"
            f"?fields={quote(fields, safe=',')}"
            f"&limit=25"
            f"&access_token={quote(token)}"
        )
    payload = request_json(url)
    items = []
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        product = str(row.get("media_product_type") or "").upper()
        media_type = str(row.get("media_type") or "").upper()
        if product != "REELS" and media_type != "REELS":
            continue
        media_id = str(row.get("id") or "").strip()
        if not media_id:
            continue
        thumb = row.get("thumbnail_url") or row.get("media_url")
        items.append(
            {
                "ig_media_id": media_id,
                "caption": row.get("caption") or None,
                "permalink": row.get("permalink") or None,
                "thumbnail_url": thumb or None,
                "published_at": _parse_timestamp(str(row.get("timestamp") or "")),
            }
        )
    next_url = ((payload.get("paging") or {}).get("next")) or None
    return {"items": items, "next_url": next_url}


def fetch_comment_usernames(media_id: str) -> list[dict]:
    creds = credentials()
    if creds is None:
        raise GraphAPIError("faltan IG_ACCESS_TOKEN o IG_USER_ID")
    token, _ig_user_id = creds
    fields = "username,timestamp"
    url = (
        f"{_base()}/{quote(media_id)}/comments"
        f"?fields={quote(fields, safe=',')}"
        f"&limit=50"
        f"&access_token={quote(token)}"
    )
    found: list[dict] = []
    pages = 0
    while url and pages < 20:
        pages += 1
        payload = request_json(url)
        for row in payload.get("data") or []:
            if not isinstance(row, dict):
                continue
            username = str(row.get("username") or "").strip().lstrip("@").lower()
            if not username or not _USERNAME_RE.fullmatch(username):
                continue
            found.append(
                {
                    "ig_username": username,
                    "created_at": _parse_timestamp(str(row.get("timestamp") or "")),
                }
            )
        url = ((payload.get("paging") or {}).get("next")) or None
    return found


def discover_profile(username: str) -> dict:
    """Business Discovery. Si la cuenta no es profesional, GraphAPIError.

    verificado queda null: la API no devuelve el tilde.
    """
    creds = credentials()
    if creds is None:
        raise GraphAPIError("faltan IG_ACCESS_TOKEN o IG_USER_ID")
    token, ig_user_id = creds
    handle = username.strip().lstrip("@")
    if not _USERNAME_RE.fullmatch(handle):
        raise GraphAPIError("username inválido para Business Discovery")

    payload = _discovery_request(ig_user_id, token, handle)
    disco = payload.get("business_discovery") if isinstance(payload, dict) else None
    if not isinstance(disco, dict):
        raise GraphAPIError("Business Discovery no devolvió business_discovery", http_status=404, code=110)

    captions = []
    media = disco.get("media") if isinstance(disco.get("media"), dict) else {}
    for item in media.get("data") or []:
        if isinstance(item, dict) and item.get("caption"):
            captions.append(str(item["caption"])[:500])
        if len(captions) >= 8:
            break

    followers = disco.get("followers_count")
    if not isinstance(followers, int):
        followers = None

    return {
        "bio": disco.get("biography") or None,
        "website": disco.get("website") or None,
        "followers": followers,
        "ultimos_captions": captions,
        "verificado": None,
        "tipo_cuenta": "profesional",
    }


def _discovery_request(ig_user_id: str, token: str, username: str) -> dict:
    expansion = f"business_discovery.username({username}){{{_DISCOVERY_FIELDS}}}"
    url = (
        f"{_base()}/{quote(ig_user_id)}"
        f"?fields={quote(expansion, safe='{},._(),')}"
        f"&access_token={quote(token)}"
    )
    return request_json(url)
