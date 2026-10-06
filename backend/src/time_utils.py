from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC naive. Pony persiste este valor como timestamp sin zona."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"
