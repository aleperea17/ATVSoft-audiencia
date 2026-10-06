import time

import pytest
from fastapi import HTTPException

from src.auth import sign_session, verify_session_token
from src.classification_json import ClassificationParseError, parse_claude_stdout
from src.graph_errors import is_profile_unavailable, is_rate_limit, is_unsupported_verified_field
from src.metrics import pct_calificado
from src.services.graph_client import redact


SECRET = "a" * 32


def test_pct_vacio_y_un_decimal():
    assert pct_calificado(0, 0) == 0.0
    assert pct_calificado(1, 3) == 33.3
    assert pct_calificado(2, 2) == 100.0


def test_sesion_hmac():
    token = sign_session({"sub": "ana", "exp": int(time.time()) + 60}, SECRET)
    payload = verify_session_token(token, SECRET)
    assert payload["sub"] == "ana"
    with pytest.raises(HTTPException):
        verify_session_token(token + "x", SECRET)
    vencido = sign_session({"sub": "ana", "exp": int(time.time()) - 120}, SECRET)
    with pytest.raises(HTTPException):
        verify_session_token(vencido, SECRET)


def test_parse_claude():
    raw = '{"type":"result","is_error":false,"result":"{\\"calificado\\": true, \\"avatar\\": \\"infoproductor\\", \\"score\\": 80, \\"motivo\\": \\"Vende mentoría\\"}"}'
    parsed = parse_claude_stdout(raw)
    assert parsed["calificado"] is True
    assert parsed["avatar"] == "infoproductor"
    with pytest.raises(ClassificationParseError):
        parse_claude_stdout('{"calificado": true}')


def test_rate_limit_y_verificado():
    assert is_rate_limit(429, None)
    assert is_rate_limit(400, 4)
    assert is_rate_limit(400, 17)
    assert is_rate_limit(400, 32)
    assert is_rate_limit(400, 613)
    assert is_rate_limit(400, 80002)
    assert not is_rate_limit(400, 100)
    assert is_unsupported_verified_field("Tried accessing nonexisting field (is_verified)")
    assert is_profile_unavailable(400, 110, "Invalid user id")
    assert not is_profile_unavailable(400, 4, "rate limit")
    assert redact("https://x?access_token=secreto&fields=a") == "https://x?access_token=REDACTED&fields=a"


def test_discovery_no_pide_verificado():
    from src.services.instagram_service import _DISCOVERY_FIELDS

    assert "is_verified" not in _DISCOVERY_FIELDS


def test_login_cookie_propia_y_limite(monkeypatch):
    import bcrypt
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.auth import AUDIENCIA_COOKIE, require_session, sign_session
    from src.services.login_services import _failures, authenticate

    _failures.clear()
    password = "clave-de-prueba"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    monkeypatch.setenv("AUDIENCIA_ADMIN_USER", "admin-prueba")
    monkeypatch.setenv("AUDIENCIA_ADMIN_PASSWORD_HASH", hashed)
    monkeypatch.setenv("AUDIENCIA_SESSION_SECRET", "b" * 32)
    monkeypatch.setenv("ECOSYSTEM_SESSION_SECRET", "c" * 32)

    app = FastAPI()
    from src.controllers.auth_controller import router

    app.include_router(router)
    client = TestClient(app)
    bad = client.post("/api/auth/login", json={"username": "admin-prueba", "password": "incorrecta"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"username": "admin-prueba", "password": password})
    assert ok.status_code == 200
    cookie = ok.headers["set-cookie"]
    assert f"{AUDIENCIA_COOKIE}=" in cookie
    assert "ecosystem_session=" not in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "samesite=lax" in cookie.lower()

    out = client.post("/api/auth/logout")
    assert "audiencia_session=" in out.headers["set-cookie"]
    assert "Max-Age=0" in out.headers["set-cookie"]

    _failures.clear()
    for _ in range(5):
        with pytest.raises(HTTPException) as failure:
            authenticate("admin-prueba", "incorrecta", "10.0.0.8")
        assert failure.value.status_code == 401
    with pytest.raises(HTTPException) as blocked:
        authenticate("admin-prueba", password, "10.0.0.8")
    assert blocked.value.status_code == 429

    propia = sign_session({"sub": "admin-prueba", "exp": int(time.time()) + 60}, "b" * 32)
    ecosistema = sign_session({"sub": "ana", "exp": int(time.time()) + 60}, "c" * 32)
    assert require_session(_request(f"audiencia_session={propia}"))["sub"] == "admin-prueba"
    assert require_session(_request(f"ecosystem_session={ecosistema}"))["sub"] == "ana"
    assert require_session(_request(f"audiencia_session=rota; ecosystem_session={ecosistema}"))["sub"] == "ana"
    with pytest.raises(HTTPException):
        require_session(_request(""))


def _request(cookie_header: str):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"cookie", cookie_header.encode())] if cookie_header else [],
        "client": ("127.0.0.1", 5000),
        "server": ("test", 80),
    }
    return Request(scope)


def test_nginx_api_no_recorta_el_prefijo():
    from pathlib import Path

    text = Path(__file__).resolve().parents[2].joinpath("nginx", "audiencia.atvos.io.conf").read_text(encoding="utf-8")
    assert "location /api/webhooks/" not in text
    assert "manychat" not in text.lower()
    assert "proxy_pass http://127.0.0.1:8020;" in text
    assert "proxy_pass http://127.0.0.1:8020/;" not in text
    assert "proxy_pass http://127.0.0.1:8020/api/" not in text
