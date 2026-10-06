from datetime import datetime

from pony.orm import LongStr, Optional, PrimaryKey, Required, Set, composite_key

from src.db import db
from src.time_utils import utcnow


class Reel(db.Entity):
    _table_ = ("audiencia", "reel")
    id = PrimaryKey(int, auto=True)
    ig_media_id = Required(str, unique=True)
    caption = Optional(LongStr)
    permalink = Optional(str)
    thumbnail_url = Optional(LongStr)
    published_at = Optional(datetime)
    keyword = Optional(str)
    comentarios_sync_at = Optional(datetime)
    interacciones = Set("Interaccion")


class Interaccion(db.Entity):
    _table_ = ("audiencia", "interaccion")
    id = PrimaryKey(int, auto=True)
    reel = Required(Reel)
    ig_username = Required(str, index=True)
    origen = Required(str)
    created_at = Required(datetime, default=utcnow)
    composite_key(reel, ig_username)


class Perfil(db.Entity):
    _table_ = ("audiencia", "perfil")
    id = PrimaryKey(int, auto=True)
    ig_username = Required(str, unique=True)
    verificado = Optional(bool)
    bio = Optional(LongStr)
    website = Optional(str)
    followers = Optional(int)
    ultimos_captions = Optional(LongStr)
    tipo_cuenta = Optional(str)
    enriquecido_at = Optional(datetime)
    clasificacion = Optional("Clasificacion")


class Clasificacion(db.Entity):
    _table_ = ("audiencia", "clasificacion")
    id = PrimaryKey(int, auto=True)
    perfil = Required(Perfil, unique=True)
    calificado = Required(bool, default=False)
    avatar = Required(str)
    score = Required(int, default=0)
    motivo = Optional(LongStr)
    clasificado_at = Required(datetime, default=utcnow)


class Rubrica(db.Entity):
    _table_ = ("audiencia", "rubrica")
    id = PrimaryKey(int, auto=True)
    texto = Required(LongStr)
    updated_at = Required(datetime, default=utcnow)


class EstadoSync(db.Entity):
    """Cursor operativo del job. No se expone en la API."""

    _table_ = ("audiencia", "estado_sync")
    id = PrimaryKey(int, auto=True)
    clave = Required(str, unique=True)
    valor = Optional(LongStr)
    updated_at = Required(datetime, default=utcnow)
