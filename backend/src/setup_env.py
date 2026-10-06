"""Carga .env de la raíz del repo y de backend/ sin pisar variables ya definidas."""

from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def _load_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def bootstrap_environment() -> None:
    global _LOADED
    if _LOADED:
        return
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    _load_file(repo_root / ".env")
    _load_file(backend_dir / ".env")
    _LOADED = True
