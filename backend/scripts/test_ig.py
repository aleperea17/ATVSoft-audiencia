"""Lectura de Instagram, sin escribir en la base.

Dentro del contenedor:

    python scripts/test_ig.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph_errors import GraphAPIError
from src.services.graph_client import redact, request_json
from src.services.instagram_service import credentials, graph_version
from src.setup_env import bootstrap_environment

bootstrap_environment()


def _stamp(unix_ts) -> str:
    if not isinstance(unix_ts, int):
        return "ausente"
    if unix_ts == 0:
        return "0 (sin vencimiento)"
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _get(url: str) -> dict:
    try:
        return request_json(url, attempts=1)
    except GraphAPIError as exc:
        print(f"ERROR {exc.http_status}: {redact(str(exc))}")
        raise SystemExit(1) from exc


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    creds = credentials()
    if creds is None:
        print("Faltan IG_ACCESS_TOKEN o IG_USER_ID")
        return 1
    token, ig_user_id = creds
    version = graph_version()
    base = f"https://graph.facebook.com/{quote(version)}"

    print("== debug_token ==")
    debug = _get(
        f"https://graph.facebook.com/{quote(version)}/debug_token"
        f"?input_token={quote(token)}&access_token={quote(token)}"
    )
    data = debug.get("data") if isinstance(debug.get("data"), dict) else {}
    valid = data.get("is_valid") is True
    scopes = data.get("scopes") or data.get("granular_scopes") or []
    scope_names = []
    for item in scopes:
        if isinstance(item, str):
            scope_names.append(item)
        elif isinstance(item, dict) and item.get("scope"):
            scope_names.append(str(item["scope"]))
    print(f"valido: {valid}")
    print(f"expires_at: {_stamp(data.get('expires_at'))}")
    print(f"data_access_expires_at: {_stamp(data.get('data_access_expires_at'))}")
    print("scopes: " + (", ".join(scope_names) if scope_names else "(ninguno)"))
    if not valid:
        return 1

    print("\n== ultimos 5 reels ==")
    media = _get(
        f"{base}/{quote(ig_user_id)}/media"
        f"?fields={quote('id,caption,permalink,timestamp,media_product_type,media_type', safe=',')}"
        f"&limit=25&access_token={quote(token)}"
    )
    reels = []
    for row in media.get("data") or []:
        if not isinstance(row, dict):
            continue
        product = str(row.get("media_product_type") or "").upper()
        media_type = str(row.get("media_type") or "").upper()
        if product == "REELS" or media_type == "REELS":
            reels.append(row)
        if len(reels) == 5:
            break
    if not reels:
        print("sin reels")
        return 0
    for index, reel in enumerate(reels, start=1):
        caption = str(reel.get("caption") or "").replace("\n", " ")[:80]
        print(f"{index}. {reel.get('id')}  {reel.get('timestamp')}  {caption}")

    first_id = str(reels[0].get("id") or "")
    print("\n== 3 comentarios del primero ==")
    comments = _get(
        f"{base}/{quote(first_id)}/comments"
        f"?fields={quote('username,timestamp', safe=',')}"
        f"&limit=3&access_token={quote(token)}"
    )
    rows = [row for row in (comments.get("data") or []) if isinstance(row, dict)][:3]
    if not rows:
        print("sin comentarios")
        return 0
    for row in rows:
        username = str(row.get("username") or "").strip().lstrip("@")
        print(f"- {username or '(sin username)'}  {row.get('timestamp')}")

    username = str(rows[0].get("username") or "").strip().lstrip("@")
    print(f"\n== business discovery de @{username or '?'} ==")
    if not username:
        print("Graph no devolvio username en el primer comentario; Business Discovery no se ejecuta")
        return 0
    fields = f"business_discovery.username({username}){{biography,website,followers_count}}"
    discovered = _get(
        f"{base}/{quote(ig_user_id)}?fields={quote(fields, safe='{},._(),')}&access_token={quote(token)}"
    )
    disco = discovered.get("business_discovery") if isinstance(discovered.get("business_discovery"), dict) else {}
    print(json.dumps(
        {
            "id": disco.get("id"),
            "followers_count": disco.get("followers_count"),
            "website": disco.get("website"),
            "biography": disco.get("biography"),
        },
        ensure_ascii=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
