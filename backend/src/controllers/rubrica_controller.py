from fastapi import APIRouter, Depends, HTTPException

from src.auth import require_session
from src.schemas import RubricaIn, RubricaOut
from src.services.rubrica_services import RubricaServices

router = APIRouter(prefix="/api/rubrica", tags=["rubrica"])
service = RubricaServices()


@router.get("", response_model=RubricaOut)
def get_rubrica(_session=Depends(require_session)):
    try:
        return service.get_rubrica()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado al leer la rúbrica") from exc


@router.put("", response_model=RubricaOut)
def put_rubrica(body: RubricaIn, _session=Depends(require_session)):
    try:
        return service.update_rubrica(body.texto)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado al guardar la rúbrica") from exc
