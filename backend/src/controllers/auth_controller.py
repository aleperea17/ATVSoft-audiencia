from fastapi import APIRouter, HTTPException, Request, Response

from src.auth import AUDIENCIA_COOKIE, SESSION_MAX_AGE
from src.schemas import LoginIn
from src.services.login_services import authenticate, client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE = {
    "key": AUDIENCIA_COOKIE,
    "path": "/",
    "httponly": True,
    "secure": True,
    "samesite": "lax",
}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        token = authenticate(body.username, body.password, client_ip(request))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error inesperado en el login") from exc
    response.set_cookie(value=token, max_age=SESSION_MAX_AGE, **_COOKIE)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(**_COOKIE)
    return {"ok": True}
