from fastapi import APIRouter, HTTPException, Request

from src.schemas import ManychatIn, ManychatOut
from src.services.webhook_services import WebhookServices

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
service = WebhookServices()


@router.post("/manychat", response_model=ManychatOut)
def manychat(body: ManychatIn, request: Request):
    try:
        return service.ingest(request, body)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado en el webhook") from exc
