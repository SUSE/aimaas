import enum

from sqlalchemy import Column, Integer, Float, String, DateTime, Date, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import CheckConstraint

from ..base_models import Mapping
from ..database import Base
from ..utils import make_aware_datetime

from .enum import ChangeStatus, EditableObjectType, ChangeType, ContentType


class ChangeValue(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)


class ChangeValueBool(ChangeValue):
    __tablename__ = 'change_values_bool'
    old_value = Column(Boolean, nullable=True)
    new_value = Column(Boolean, nullable=True)


class ChangeValueInt(ChangeValue):
    __tablename__ = 'change_values_int'
    old_value = Column(Integer, nullable=True)
    new_value = Column(Integer, nullable=True)


class ChangeValueFloat(ChangeValue):
    __tablename__ = 'change_values_float'
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=True)


class ChangeValueForeignKey(ChangeValue):
    __tablename__ = 'change_values_fk'
    old_value = Column(Integer, nullable=True)
    new_value = Column(Integer, nullable=True)


class ChangeValueStr(ChangeValue):
    __tablename__ = 'change_values_str'
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)


class ChangeValueDatetime(ChangeValue):
    __tablename__ = 'change_values_datetime'
    old_value = Column(DateTime(timezone=True), nullable=True)
    new_value = Column(DateTime(timezone=True), nullable=True)


class ChangeValueDate(ChangeValue):
    __tablename__ = 'change_values_date'
    old_value = Column(Date, nullable=True)
    new_value = Column(Date, nullable=True)


class ChangeAttrType(enum.Enum):
    STR = Mapping(ChangeValueStr, str)
    BOOL = Mapping(ChangeValueBool, bool)
    INT = Mapping(ChangeValueInt, int)
    FLOAT = Mapping(ChangeValueFloat, float)
    FK = Mapping(ChangeValueForeignKey, int)
    DT = Mapping(ChangeValueDatetime, make_aware_datetime)
    DATE = Mapping(ChangeValueDate, lambda x: x)


class ChangeRequest(Base):
    __tablename__ = 'change_requests'
    id = Column(Integer, primary_key=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey('users.id'))

    created_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ChangeStatus), default=ChangeStatus.PENDING, nullable=False)
    comment = Column(String(1024), nullable=True)
    object_type = Column(Enum(EditableObjectType), nullable=False)
    change_type = Column(Enum(ChangeType), nullable=False)

    created_by = relationship('User', foreign_keys=[created_by_user_id])
    reviewed_by = relationship('User', foreign_keys=[reviewed_by_user_id])


class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    change_request_id = Column(Integer, ForeignKey('change_requests.id'), nullable=False)
    attribute_id = Column(Integer, ForeignKey('attributes.id'), nullable=True)

    object_id = Column(Integer, nullable=True)
    value_id = Column(Integer, nullable=False)
    content_type = Column(Enum(ContentType), nullable=False)
    change_type = Column(Enum(ChangeType), nullable=False)
    field_name = Column(String, nullable=True)
    data_type = Column(Enum(ChangeAttrType), nullable=False)

    change_request = relationship('ChangeRequest')
    attribute = relationship('Attribute')

    __table_args__ = (
        CheckConstraint('NOT(attribute_id IS NULL AND field_name IS NULL)'),
    )