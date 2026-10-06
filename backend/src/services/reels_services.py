from fastapi import HTTPException
from pony.orm import db_session

from src.metrics import pct_calificado
from src.models import Clasificacion, Interaccion, Perfil, Reel
from src.time_utils import iso_z


class ReelsServices:
    def list_reels(self) -> list[dict]:
        with db_session:
            reels = list(Reel.select()[:])
            interacciones = list(Interaccion.select()[:])
            perfiles = list(Perfil.select()[:])
            clasificaciones = list(Clasificacion.select()[:])

            perfil_por_user = {p.ig_username: p for p in perfiles}
            calificado_por_perfil = {c.perfil.id: c.calificado for c in clasificaciones}

            usuarios_por_reel: dict[int, set[str]] = {}
            for row in interacciones:
                usuarios_por_reel.setdefault(row.reel.id, set()).add(row.ig_username)

            payload = []
            for reel in reels:
                usuarios = usuarios_por_reel.get(reel.id, set())
                calificados = 0
                for username in usuarios:
                    perfil = perfil_por_user.get(username)
                    if perfil is None:
                        continue
                    if calificado_por_perfil.get(perfil.id):
                        calificados += 1
                total = len(usuarios)
                payload.append(
                    {
                        "id": reel.id,
                        "ig_media_id": reel.ig_media_id,
                        "caption": reel.caption,
                        "permalink": reel.permalink,
                        "thumbnail_url": reel.thumbnail_url,
                        "published_at": iso_z(reel.published_at),
                        "keyword": reel.keyword,
                        "total_interacciones": total,
                        "calificados": calificados,
                        "pct_calificado": pct_calificado(calificados, total),
                    }
                )

        payload.sort(key=lambda item: item["published_at"] or "", reverse=True)
        return payload

    def list_calificados(self, reel_id: int, limit: int, offset: int) -> dict:
        limit = min(max(int(limit), 1), 50)
        offset = max(int(offset), 0)
        with db_session:
            reel = Reel.get(id=reel_id)
            if reel is None:
                raise HTTPException(status_code=404, detail="Reel no encontrado")

            usuarios = {
                row.ig_username
                for row in list(Interaccion.select()[:])
                if row.reel.id == reel_id
            }
            items = []
            for perfil in list(Perfil.select()[:]):
                if perfil.ig_username not in usuarios:
                    continue
                clasif = perfil.clasificacion
                if clasif is None or not clasif.calificado:
                    continue
                items.append(
                    {
                        "ig_username": perfil.ig_username,
                        "verificado": perfil.verificado,
                        "bio": perfil.bio,
                        "avatar": clasif.avatar,
                        "score": clasif.score,
                        "motivo": clasif.motivo,
                    }
                )

        items.sort(key=lambda item: (-item["score"], item["ig_username"]))
        total = len(items)
        return {
            "reel_id": reel_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items[offset : offset + limit],
        }
