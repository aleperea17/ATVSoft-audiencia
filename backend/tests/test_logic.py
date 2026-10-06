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


def test_nginx_api_no_recorta_el_prefijo():
    from pathlib import Path

    text = Path(__file__).resolve().parents[2].joinpath("nginx", "audiencia.atvos.io.conf").read_text(encoding="utf-8")
    assert "location /api/webhooks/" not in text
    assert "manychat" not in text.lower()
    assert "proxy_pass http://127.0.0.1:8020;" in text
    assert "proxy_pass http://127.0.0.1:8020/;" not in text
    assert "proxy_pass http://127.0.0.1:8020/api/" not in text
