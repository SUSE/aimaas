from datetime import datetime
import typing

from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import StrategizedProperty

from .config import settings
from .database import Base


def make_aware_datetime(dt: datetime) -> datetime:
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=settings.timezone)
    return dt


def iterate_model_fields(model: Base) -> typing.Dict[str, StrategizedProperty]:
    return {prop.key: prop for prop in class_mapper(model).iterate_properties}
