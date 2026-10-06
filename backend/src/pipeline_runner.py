"""Una pasada del pipeline, sin esperar los 30 minutos.

Uso dentro del contenedor:

    python -m src.pipeline_runner run-once
"""

from __future__ import annotations

import asyncio
import sys

from src.setup_env import bootstrap_environment

bootstrap_environment()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["run-once"]:
        print("Uso: python -m src.pipeline_runner run-once", file=sys.stderr)
        return 2
    from src.db import init_db
    from src.services.pipeline_services import PipelineServices

    init_db()
    asyncio.run(PipelineServices().run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
