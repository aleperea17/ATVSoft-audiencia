import hmac
import re

from decouple import config
from fastapi import HTTPException, Request
from pony.orm import db_session

from src.keyword_match import pick_reel_for_keyword
from src.models import Interaccion, Reel
from src.schemas import ManychatIn
from src.time_utils import utcnow

_USERNAME_RE = re.compile(r"^[a-z0-9._]{1,30}$")


class WebhookServices:
    def ingest(self, request: Request, body: ManychatIn) -> dict:
        expected = (config("MANYCHAT_WEBHOOK_TOKEN", default="") or "").strip()
        if len(expected) < 16:
            raise HTTPException(status_code=503, detail="Webhook sin token configurado")
        given = self._presented_token(request, body)
        if not given or not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
            raise HTTPException(status_code=401, detail="Token de webhook inválido")

        username = self._username(body)
        keyword = self._keyword(body)
        if not username or not _USERNAME_RE.fullmatch(username):
            raise HTTPException(status_code=400, detail="Falta un username de Instagram válido")
        if not keyword:
            raise HTTPException(status_code=400, detail="Falta la keyword")

        with db_session:
            reels = list(Reel.select()[:])
            reel, persist = pick_reel_for_keyword(reels, keyword)
            if reel is None:
                raise HTTPException(
                    status_code=404,
                    detail="Ningún reel coincide con esa keyword",
                )
            if persist and not (reel.keyword or "").strip():
                reel.keyword = keyword.strip()

            existing = Interaccion.get(reel=reel, ig_username=username)
            created = existing is None
            if created:
                Interaccion(
                    reel=reel,
                    ig_username=username,
                    origen="manychat",
                    created_at=utcnow(),
                )
            reel_id = reel.id

        return {"ok": True, "created": created, "reel_id": reel_id, "ig_username": username}

    def _presented_token(self, request: Request, body: ManychatIn) -> str:
        header = (request.headers.get("x-webhook-token") or "").strip()
        if header:
            return header
        auth = (request.headers.get("authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return (body.token or "").strip()

    def _username(self, body: ManychatIn) -> str:
        extra = body.model_extra or {}
        candidates = [body.username, body.ig_username, body.user_name, extra.get("username"), extra.get("ig_username")]
        for candidate in candidates:
            if candidate is None:
                continue
            cleaned = str(candidate).strip().lstrip("@").lower()
            if cleaned:
                return cleaned
        return ""

    def _keyword(self, body: ManychatIn) -> str:
        extra = body.model_extra or {}
        raw = body.keyword or extra.get("keyword") or extra.get("key_word")
        return str(raw).strip() if raw else ""
