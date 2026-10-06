from pydantic import BaseModel, Field


class ReelOut(BaseModel):
    id: int
    ig_media_id: str
    caption: str | None = None
    permalink: str | None = None
    thumbnail_url: str | None = None
    published_at: str | None = None
    keyword: str | None = None
    total_interacciones: int
    calificados: int
    pct_calificado: float


class CalificadoOut(BaseModel):
    ig_username: str
    verificado: bool | None = None
    bio: str | None = None
    avatar: str
    score: int
    motivo: str | None = None


class CalificadosPage(BaseModel):
    reel_id: int
    total: int
    limit: int
    offset: int
    items: list[CalificadoOut]


class RubricaOut(BaseModel):
    texto: str
    updated_at: str | None = None


class RubricaIn(BaseModel):
    texto: str = Field(min_length=10, max_length=8000)


class ManychatIn(BaseModel):
    username: str | None = None
    ig_username: str | None = None
    user_name: str | None = None
    keyword: str | None = None
    token: str | None = None

    model_config = {"extra": "allow"}


class ManychatOut(BaseModel):
    ok: bool
    created: bool
    reel_id: int
    ig_username: str
