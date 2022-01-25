from datetime import datetime

from .config import settings


def make_aware_datetime(dt: datetime) -> datetime:
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=settings.timezone)
    return dt
