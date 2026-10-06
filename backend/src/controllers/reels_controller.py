from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.auth import require_session
from src.schemas import CalificadosPage, ReelOut
from src.services.reels_services import ReelsServices

router = APIRouter(prefix="/api/reels", tags=["reels"])
service = ReelsServices()


@router.get("", response_model=list[ReelOut])
def list_reels(response: Response, _session=Depends(require_session)):
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.list_reels()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado al listar reels") from exc


@router.get("/{reel_id}/calificados", response_model=CalificadosPage)
def list_calificados(
    reel_id: int,
    response: Response,
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _session=Depends(require_session),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.list_calificados(reel_id, limit, offset)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado al listar calificados") from exc
