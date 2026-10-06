"""Job: reels → comentarios → Business Discovery → Claude."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from decouple import config
from pony.orm import db_session

from src.graph_errors import GraphAPIError, GraphRateLimitError, is_profile_unavailable
from src.models import Clasificacion, EstadoSync, Interaccion, Perfil, Reel, Rubrica
from src.services.classification_service import classify_profile
from src.services.instagram_service import (
    credentials,
    discover_profile,
    fetch_comment_usernames,
    fetch_reel_page,
)
from src.time_utils import utcnow

logger = logging.getLogger("audiencia.pipeline")

STALE_AFTER = timedelta(days=30)
BACKFILL_PAGES_PER_RUN = 4

_lock = asyncio.Lock()


def _optional_limit(name: str) -> int | None:
    """None si la variable no está: en ese caso el pipeline no corta por cantidad."""
    raw = (config(name, default="") or "").strip()
    if not raw:
        return None
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning("%s=%r no es un entero; se procesa sin tope", name, raw)
        return None


def _is_stale(moment) -> bool:
    if moment is None:
        return True
    return moment < utcnow() - STALE_AFTER


class PipelineServices:
    async def run(self) -> None:
        if _lock.locked():
            logger.info("pipeline ya en curso, se saltea esta vuelta")
            return
        async with _lock:
            if credentials() is None:
                logger.warning("sin IG_ACCESS_TOKEN / IG_USER_ID; se saltea la ingesta")
            else:
                await self._ingest_reels()
                await self._ingest_comments()
                await self._enrich()
            await self._classify()

    async def _ingest_reels(self) -> None:
        limit = _optional_limit("PIPELINE_MAX_REELS")
        if limit is not None:
            await self._ingest_newest_reels(limit)
            return
        done, next_url = await asyncio.to_thread(_read_reel_cursor)
        # Con el historial ya cargado se refrescan 2 páginas (los reels más nuevos).
        pages = 2 if done else BACKFILL_PAGES_PER_RUN
        url = None if done else next_url
        for _ in range(pages):
            try:
                page = await asyncio.to_thread(fetch_reel_page, url)
            except GraphRateLimitError as exc:
                logger.warning("ingesta de reels frenada por rate limit: %s", exc)
                return
            except GraphAPIError as exc:
                logger.error("ingesta de reels falló: %s", exc)
                return
            await asyncio.to_thread(_upsert_reels, page["items"])
            url = page["next_url"]
            if not url:
                if not done:
                    await asyncio.to_thread(_write_cursor, "", True)
                    logger.info("backfill de reels completo")
                return
            if not done:
                await asyncio.to_thread(_write_cursor, url, False)

    async def _ingest_newest_reels(self, limit: int) -> None:
        url = None
        stored = 0
        pages = 0
        while stored < limit and pages < 40:
            pages += 1
            try:
                page = await asyncio.to_thread(fetch_reel_page, url)
            except GraphRateLimitError as exc:
                logger.warning("ingesta de reels frenada por rate limit: %s", exc)
                return
            except GraphAPIError as exc:
                logger.error("ingesta de reels falló: %s", exc)
                return
            room = limit - stored
            items = page["items"][:room]
            if items:
                await asyncio.to_thread(_upsert_reels, items)
                stored += len(items)
            url = page["next_url"]
            if not url:
                return

    async def _ingest_comments(self) -> None:
        media_ids = await asyncio.to_thread(_reels_pending_comments)
        for media_id, reel_id in media_ids:
            try:
                comments = await asyncio.to_thread(fetch_comment_usernames, media_id)
            except GraphRateLimitError as exc:
                logger.warning("comentarios frenados por rate limit: %s", exc)
                return
            except GraphAPIError as exc:
                logger.error("comentarios de %s fallaron: %s", media_id, exc)
                await asyncio.to_thread(_touch_comment_sync, reel_id)
                continue
            await asyncio.to_thread(_upsert_comments, reel_id, comments)

    async def _enrich(self) -> None:
        usernames = await asyncio.to_thread(_usernames_to_enrich)
        for username in usernames:
            try:
                discovered = await asyncio.to_thread(discover_profile, username)
            except GraphRateLimitError as exc:
                logger.warning("enriquecimiento frenado por rate limit: %s", exc)
                return
            except GraphAPIError as exc:
                if is_profile_unavailable(exc.http_status, exc.code, str(exc)):
                    await asyncio.to_thread(_save_sin_datos, username)
                    continue
                logger.error("business discovery de @%s falló: %s", username, exc)
                continue
            await asyncio.to_thread(_save_discovered, username, discovered)

    async def _classify(self) -> None:
        rubrica, pending = await asyncio.to_thread(_pending_profiles)
        if not rubrica:
            logger.error("no hay rúbrica; no se clasifica")
            return
        for perfil in pending:
            if perfil["tipo_cuenta"] == "personal_o_inaccesible":
                continue
            result = await asyncio.to_thread(classify_profile, perfil, rubrica)
            if result is None:
                continue
            await asyncio.to_thread(_save_classification, perfil["id"], result)


def _read_reel_cursor() -> tuple[bool, str | None]:
    with db_session:
        done_row = EstadoSync.get(clave="reels_backfill_done")
        next_row = EstadoSync.get(clave="reels_next_url")
        done = bool(done_row and (done_row.valor or "") == "1")
        nxt = (next_row.valor or "").strip() if next_row else ""
        return done, (nxt or None)


def _write_cursor(next_url: str, done: bool) -> None:
    with db_session:
        _set_state("reels_next_url", next_url)
        _set_state("reels_backfill_done", "1" if done else "0")


def _set_state(clave: str, valor: str) -> None:
    row = EstadoSync.get(clave=clave)
    now = utcnow()
    if row is None:
        EstadoSync(clave=clave, valor=valor, updated_at=now)
        return
    row.valor = valor
    row.updated_at = now


def _upsert_reels(items: list[dict]) -> None:
    with db_session:
        for item in items:
            row = Reel.get(ig_media_id=item["ig_media_id"])
            if row is None:
                Reel(
                    ig_media_id=item["ig_media_id"],
                    caption=item.get("caption"),
                    permalink=item.get("permalink"),
                    thumbnail_url=item.get("thumbnail_url"),
                    published_at=item.get("published_at"),
                )
                continue
            row.caption = item.get("caption")
            row.permalink = item.get("permalink")
            row.thumbnail_url = item.get("thumbnail_url")
            row.published_at = item.get("published_at")


def _reels_pending_comments() -> list[tuple[str, int]]:
    with db_session:
        rows = list(Reel.select()[:])
        limit = _optional_limit("PIPELINE_MAX_REELS")
        if limit is not None:
            rows.sort(key=lambda reel: reel.published_at or datetime.min, reverse=True)
            rows = rows[:limit]
        else:
            rows.sort(key=lambda reel: (reel.comentarios_sync_at is not None, reel.comentarios_sync_at or utcnow()))
        return [(reel.ig_media_id, reel.id) for reel in rows]


def _touch_comment_sync(reel_id: int) -> None:
    with db_session:
        reel = Reel.get(id=reel_id)
        if reel is not None:
            reel.comentarios_sync_at = utcnow()


def _upsert_comments(reel_id: int, comments: list[dict]) -> None:
    with db_session:
        reel = Reel.get(id=reel_id)
        if reel is None:
            return
        for comment in comments:
            username = comment["ig_username"]
            if Interaccion.get(reel=reel, ig_username=username) is None:
                Interaccion(
                    reel=reel,
                    ig_username=username,
                    origen="comentario",
                    created_at=comment.get("created_at") or utcnow(),
                )
        reel.comentarios_sync_at = utcnow()


def _usernames_to_enrich() -> list[str]:
    with db_session:
        seen: list[str] = []
        known = {row.ig_username for row in list(Interaccion.select()[:])}
        perfiles = {row.ig_username: row for row in list(Perfil.select()[:])}
        limit = _optional_limit("PIPELINE_MAX_PERFILES")
        for username in sorted(known):
            perfil = perfiles.get(username)
            if perfil is not None and not _is_stale(perfil.enriquecido_at):
                continue
            if limit is not None and len(seen) >= limit:
                break
            seen.append(username)
        return seen


def _save_sin_datos(username: str) -> None:
    with db_session:
        perfil = _ensure_perfil(username)
        perfil.verificado = None
        perfil.tipo_cuenta = "personal_o_inaccesible"
        perfil.enriquecido_at = utcnow()
        _write_clasificacion(
            perfil,
            {
                "calificado": False,
                "avatar": "sin_datos",
                "score": 0,
                "motivo": "Cuenta personal o sin datos públicos de Business Discovery.",
            },
        )


def _save_discovered(username: str, discovered: dict) -> None:
    with db_session:
        perfil = _ensure_perfil(username)
        perfil.bio = discovered.get("bio")
        perfil.website = discovered.get("website")
        perfil.followers = discovered.get("followers")
        perfil.ultimos_captions = json.dumps(discovered.get("ultimos_captions") or [], ensure_ascii=False)
        perfil.verificado = None
        perfil.tipo_cuenta = discovered.get("tipo_cuenta") or "profesional"
        perfil.enriquecido_at = utcnow()
        clasif = perfil.clasificacion
        if clasif is not None and clasif.avatar == "sin_datos":
            clasif.delete()


def _ensure_perfil(username: str) -> Perfil:
    perfil = Perfil.get(ig_username=username)
    if perfil is None:
        perfil = Perfil(ig_username=username)
    return perfil


def _pending_profiles() -> tuple[str, list[dict]]:
    with db_session:
        rows = list(Rubrica.select()[:])
        rows.sort(key=lambda item: item.id)
        rubrica = rows[0].texto if rows else ""
        pending = []
        limit = _optional_limit("PIPELINE_MAX_PERFILES")
        for perfil in list(Perfil.select()[:]):
            if perfil.enriquecido_at is None:
                continue
            clasif = perfil.clasificacion
            if clasif is not None and not _is_stale(clasif.clasificado_at):
                continue
            if perfil.tipo_cuenta == "personal_o_inaccesible":
                continue
            if limit is not None and len(pending) >= limit:
                break
            captions = []
            if perfil.ultimos_captions:
                try:
                    parsed = json.loads(perfil.ultimos_captions)
                    if isinstance(parsed, list):
                        captions = parsed
                except json.JSONDecodeError:
                    captions = [perfil.ultimos_captions]
            pending.append(
                {
                    "id": perfil.id,
                    "ig_username": perfil.ig_username,
                    "verificado": perfil.verificado,
                    "bio": perfil.bio,
                    "website": perfil.website,
                    "followers": perfil.followers,
                    "ultimos_captions": captions,
                    "tipo_cuenta": perfil.tipo_cuenta,
                }
            )
        return rubrica, pending


def _save_classification(perfil_id: int, result: dict) -> None:
    with db_session:
        perfil = Perfil.get(id=perfil_id)
        if perfil is None:
            return
        _write_clasificacion(perfil, result)


def _write_clasificacion(perfil: Perfil, result: dict) -> None:
    clasif = perfil.clasificacion
    now = utcnow()
    if clasif is None:
        Clasificacion(
            perfil=perfil,
            calificado=bool(result["calificado"]),
            avatar=result["avatar"],
            score=int(result["score"]),
            motivo=result.get("motivo"),
            clasificado_at=now,
        )
        return
    clasif.calificado = bool(result["calificado"])
    clasif.avatar = result["avatar"]
    clasif.score = int(result["score"])
    clasif.motivo = result.get("motivo")
    clasif.clasificado_at = now
