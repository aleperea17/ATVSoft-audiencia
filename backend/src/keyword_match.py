"""Mapea la keyword de ManyChat al reel, sin UI de keywords."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def _published(reel: Any) -> datetime:
    value = getattr(reel, "published_at", None)
    if isinstance(value, datetime):
        return value
    return datetime.min


def _keyword_of(reel: Any) -> str:
    return (getattr(reel, "keyword", None) or "").strip().lower()


def _caption_has_keyword(caption: str | None, keyword: str) -> bool:
    text = caption or ""
    return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, flags=re.IGNORECASE) is not None


def pick_reel_for_keyword(reels: list[Any], keyword: str) -> tuple[Any | None, bool]:
    """Devuelve (reel, persistir_keyword).

    1. Coincidencia exacta de reel.keyword (case-insensitive). Gana el más reciente.
    2. Si no hay, el reel más reciente cuya caption contiene la keyword como palabra
       y que todavía no tiene otra keyword guardada. En ese caso persistir_keyword=True.
    """
    needle = (keyword or "").strip().lower()
    if not needle:
        return None, False

    exact = [reel for reel in reels if _keyword_of(reel) == needle]
    if exact:
        return max(exact, key=_published), False

    caption_hits = [
        reel
        for reel in reels
        if not _keyword_of(reel) and _caption_has_keyword(getattr(reel, "caption", None), needle)
    ]
    if not caption_hits:
        return None, False
    return max(caption_hits, key=_published), True
