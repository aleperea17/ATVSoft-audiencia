"""Parseo estricto del JSON que debe devolver Claude CLI."""

from __future__ import annotations

import json
import re

ALLOWED_AVATARS = ("infoproductor", "growth_operator", "otro", "sin_datos")
QUALIFIED_AVATARS = ("infoproductor", "growth_operator")


class ClassificationParseError(ValueError):
    pass


def _extract_object(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ClassificationParseError("respuesta vacía")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ClassificationParseError("no hay objeto JSON")
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ClassificationParseError("JSON inválido") from exc
    if not isinstance(parsed, dict):
        raise ClassificationParseError("el JSON no es un objeto")
    return parsed


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise ClassificationParseError("calificado debe ser bool")


def _as_score(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClassificationParseError("score debe ser numérico")
    score = int(round(float(value)))
    if score < 0 or score > 100:
        raise ClassificationParseError("score fuera de 0–100")
    return score


def parse_claude_stdout(stdout: str) -> dict:
    """Acepta el JSON directo o el sobre de `claude --output-format json`."""
    outer = _extract_object(stdout)
    if outer.get("is_error") is True:
        detail = outer.get("result") or outer.get("error") or "claude devolvió error"
        raise ClassificationParseError(str(detail)[:300])
    if "calificado" in outer and "avatar" in outer:
        return _validate_fields(outer)
    result = outer.get("result")
    if isinstance(result, dict):
        return _validate_fields(result)
    if isinstance(result, str):
        return _validate_fields(_extract_object(result))
    raise ClassificationParseError("el sobre de Claude no trae result")


def _validate_fields(data: dict) -> dict:
    if "calificado" not in data or "avatar" not in data or "score" not in data or "motivo" not in data:
        raise ClassificationParseError("faltan claves calificado, avatar, score o motivo")
    avatar = str(data.get("avatar") or "").strip().lower()
    if avatar not in ALLOWED_AVATARS:
        raise ClassificationParseError("avatar no permitido")
    motivo = data.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        raise ClassificationParseError("motivo vacío")
    return {
        "calificado": _as_bool(data.get("calificado")),
        "avatar": avatar,
        "score": _as_score(data.get("score")),
        "motivo": motivo.strip()[:500],
    }


def apply_rubric_gate(parsed: dict, verificado: bool | None) -> dict:
    """La rúbrica exige cuenta verificada Y avatar infoproductor o growth operator.

    Si el tilde no vino (None), no se considera verificado.
    """
    out = dict(parsed)
    avatar_ok = out["avatar"] in QUALIFIED_AVATARS
    if verificado is not True or not avatar_ok:
        out["calificado"] = False
    return out
