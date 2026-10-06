"""Errores de Instagram Graph API y detección de rate limit."""

from __future__ import annotations

RATE_LIMIT_CODES = {4, 17, 32, 613, 80002}


class GraphAPIError(Exception):
    def __init__(self, message: str, *, http_status: int | None = None, code: int | None = None):
        super().__init__(message)
        self.http_status = http_status
        self.code = code


class GraphRateLimitError(GraphAPIError):
    pass


def is_rate_limit(http_status: int | None, code: int | None) -> bool:
    if http_status == 429:
        return True
    return code in RATE_LIMIT_CODES


def is_unsupported_verified_field(message: str) -> bool:
    msg = (message or "").lower()
    return "is_verified" in msg or ("nonexisting field" in msg and "verif" in msg)


def is_profile_unavailable(http_status: int | None, code: int | None, message: str) -> bool:
    """Cuenta personal, inexistente o no visible para Business Discovery."""
    if is_rate_limit(http_status, code) or is_unsupported_verified_field(message):
        return False
    msg = (message or "").lower()
    if code in {110, 210}:
        return True
    hints = (
        "invalid user",
        "cannot find",
        "not a business",
        "nonexisting user",
        "user not visible",
        "does not exist",
        "isn't a business",
        "is not a business",
        "personal account",
    )
    if any(hint in msg for hint in hints):
        return True
    if code == 100 and "field" not in msg and "parameter" not in msg:
        return True
    return False
