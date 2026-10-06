"""Emite una cookie ecosystem_session para probar el módulo en local.

Uso (desde backend/, con ECOSYSTEM_SESSION_SECRET en el entorno):

    python scripts/mint_session.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auth import session_secret, sign_session  # noqa: E402
from src.setup_env import bootstrap_environment  # noqa: E402

bootstrap_environment()


def main() -> None:
    secret = session_secret()
    if len(secret) < 32:
        raise SystemExit("ECOSYSTEM_SESSION_SECRET debe tener al menos 32 caracteres")
    token = sign_session({"sub": "local", "exp": int(time.time()) + 60 * 60 * 12}, secret)
    print(token)


if __name__ == "__main__":
    main()
