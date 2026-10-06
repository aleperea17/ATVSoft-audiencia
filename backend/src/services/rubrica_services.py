from fastapi import HTTPException
from pony.orm import db_session

from src.models import Rubrica
from src.time_utils import iso_z, utcnow


class RubricaServices:
    def get_rubrica(self) -> dict:
        with db_session:
            row = self._row()
            return {"texto": row.texto, "updated_at": iso_z(row.updated_at)}

    def update_rubrica(self, texto: str) -> dict:
        cleaned = texto.strip()
        if len(cleaned) < 10:
            raise HTTPException(status_code=400, detail="La rúbrica es demasiado corta")
        with db_session:
            row = self._row()
            row.texto = cleaned
            row.updated_at = utcnow()
            return {"texto": row.texto, "updated_at": iso_z(row.updated_at)}

    def _row(self) -> Rubrica:
        rows = list(Rubrica.select()[:])
        if not rows:
            raise HTTPException(status_code=404, detail="No hay rúbrica cargada")
        rows.sort(key=lambda item: item.id)
        return rows[0]
