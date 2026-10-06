from __future__ import annotations

import logging

from decouple import config
from pony.orm import Database, db_session

from src.setup_env import bootstrap_environment

bootstrap_environment()

logger = logging.getLogger("audiencia.db")

db = Database()
_mapped = False

RUBRICA_INICIAL = (
    "Calificado = avatar infoproductor o growth operator, según bio, web y captions. "
    "Más de 5.000 seguidores suma confianza, pero no es excluyente."
)

_COLUMN_DEFAULTS = (
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS ig_media_id TEXT",
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS caption TEXT",
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS permalink TEXT",
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS thumbnail_url TEXT",
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS published_at TIMESTAMP",
    "ALTER TABLE audiencia.reel ADD COLUMN IF NOT EXISTS comentarios_sync_at TIMESTAMP",
    "ALTER TABLE audiencia.interaccion ADD COLUMN IF NOT EXISTS origen TEXT DEFAULT 'comentario'",
    "ALTER TABLE audiencia.interaccion ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS verificado BOOLEAN",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS bio TEXT",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS website TEXT",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS followers INTEGER",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS ultimos_captions TEXT",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS tipo_cuenta TEXT",
    "ALTER TABLE audiencia.perfil ADD COLUMN IF NOT EXISTS enriquecido_at TIMESTAMP",
    "ALTER TABLE audiencia.clasificacion ADD COLUMN IF NOT EXISTS calificado BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE audiencia.clasificacion ADD COLUMN IF NOT EXISTS avatar TEXT DEFAULT 'sin_datos'",
    "ALTER TABLE audiencia.clasificacion ADD COLUMN IF NOT EXISTS score INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE audiencia.clasificacion ADD COLUMN IF NOT EXISTS motivo TEXT",
    "ALTER TABLE audiencia.clasificacion ADD COLUMN IF NOT EXISTS clasificado_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE audiencia.rubrica ADD COLUMN IF NOT EXISTS texto TEXT DEFAULT ''",
    "ALTER TABLE audiencia.rubrica ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE audiencia.estado_sync ADD COLUMN IF NOT EXISTS valor TEXT",
    "ALTER TABLE audiencia.estado_sync ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
)


def _db_kwargs() -> dict:
    user = (config("POSTGRES_USER", default="") or "").strip()
    password = (config("POSTGRES_PASSWORD", default="") or "").strip()
    host = (config("DB_HOST", default="") or "").strip()
    name = (config("POSTGRES_DB", default="") or "").strip()
    if not user or not password or not host or not name:
        raise RuntimeError("Faltan POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB o DB_HOST.")
    port = int((config("DB_PORT", default="5432") or "5432").strip())
    return {"user": user, "password": password, "host": host, "port": port, "database": name}


def _bind() -> None:
    settings = _db_kwargs()
    db.bind(provider="postgres", **settings)


_bind()


def _connect_psycopg():
    import psycopg2

    settings = _db_kwargs()
    return psycopg2.connect(
        user=settings["user"],
        password=settings["password"],
        host=settings["host"],
        port=settings["port"],
        dbname=settings["database"],
    )


def _create_schema() -> None:
    conn = _connect_psycopg()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS audiencia")
    finally:
        conn.close()


def _ensure_columns() -> None:
    conn = _connect_psycopg()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            for statement in _COLUMN_DEFAULTS:
                cur.execute(statement)
    finally:
        conn.close()


def _seed_rubrica() -> None:
    from src.models import Rubrica
    from src.time_utils import utcnow

    with db_session:
        rows = list(Rubrica.select()[:])
        if rows:
            return
        Rubrica(texto=RUBRICA_INICIAL, updated_at=utcnow())


def init_db() -> None:
    global _mapped
    from src import models  # noqa: F401

    _create_schema()
    if not _mapped:
        db.generate_mapping(create_tables=True)
        _mapped = True
    _ensure_columns()
    _seed_rubrica()
    logger.info("schema audiencia listo")
