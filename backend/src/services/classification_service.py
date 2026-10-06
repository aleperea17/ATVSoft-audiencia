"""Clasificación vía Claude CLI (subprocess, --output-format json). No usa el SDK."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

from decouple import config

from src.classification_json import ClassificationParseError, parse_claude_stdout

logger = logging.getLogger("audiencia.claude")


def _build_prompt(rubrica: str, perfil: dict) -> str:
    captions = perfil.get("ultimos_captions") or []
    if isinstance(captions, str):
        captions_text = captions
    else:
        captions_text = "\n---\n".join(str(item) for item in captions[:8])
    verificado = perfil.get("verificado")
    if verificado is True:
        verificado_txt = "true"
    elif verificado is False:
        verificado_txt = "false"
    else:
        verificado_txt = "null"
    return f"""Devolvé ÚNICAMENTE un objeto JSON válido, sin markdown y sin texto alrededor.
Claves obligatorias:
- calificado: boolean
- avatar: uno de "infoproductor", "growth_operator", "otro", "sin_datos"
- score: entero de 0 a 100
- motivo: string corto en español

RÚBRICA:
{rubrica}

PERFIL DE INSTAGRAM:
username: {perfil.get("ig_username")}
verificado: {verificado_txt}
bio: {perfil.get("bio") or ""}
website: {perfil.get("website") or ""}
followers_count: {perfil.get("followers") if perfil.get("followers") is not None else "null"}
ultimos_captions:
{captions_text}
"""


def _run_claude(prompt: str) -> str:
    binary = (config("CLAUDE_BIN", default="claude") or "claude").strip()
    cmd = [
        binary,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
    ]
    env = os.environ.copy()
    api_key = (config("ANTHROPIC_API_KEY", default="") or "").strip()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env.setdefault("CI", "1")
    cwd = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=cwd,
        check=False,
    )
    stdout = completed.stdout or ""
    if completed.returncode != 0 and not stdout.strip():
        err = (completed.stderr or "").strip()[:400]
        raise ClassificationParseError(err or f"claude exit {completed.returncode}")
    return stdout


def classify_profile(perfil: dict, rubrica: str) -> dict | None:
    """Reintenta una vez si el JSON es inválido. None si falla las dos."""
    prompt = _build_prompt(rubrica, perfil)
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            stdout = _run_claude(prompt)
            return parse_claude_stdout(stdout)
        except (ClassificationParseError, subprocess.TimeoutExpired, OSError) as exc:
            last_error = exc
            logger.warning(
                "clasificación de @%s intento %s falló: %s",
                perfil.get("ig_username"),
                attempt,
                exc,
            )
    logger.error("clasificación agotada para @%s: %s", perfil.get("ig_username"), last_error)
    return None
