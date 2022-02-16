import enum
from typing import List, Union, Optional

from sqlalchemy import (
    select, Enum, DateTime, Date,
    Boolean, Column, ForeignKey,
    Integer, String, Float)
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.schema import UniqueConstraint

from .base_models import Value, Mapping
from .database import Base
from .enum import FilterEnum
from .utils import make_aware_datetime


class ValueBool(Value):
    __tablename__ = 'values_bool'
    value = Column(Boolean)


class ValueInt(Value):
    __tablename__ = 'values_int'
    value = Column(Integer)


class ValueFloat(Value):
    __tablename__ = 'values_float'
    value = Column(Float)


class ValueForeignKey(Value):
    __tablename__ = 'values_fk'
    value = Column(Integer)


class ValueStr(Value):
    __tablename__ = 'values_str'
    value = Column(String)


class ValueDatetime(Value):
    __tablename__ = 'values_datetime'
    value = Column(DateTime(timezone=True))

class ValueDate(Value):
    __tablename__ = 'values_date'
    value = Column(Date)


class AttrType(enum.Enum):
    STR = Mapping(ValueStr, str, [FilterEnum.EQ, FilterEnum.LT, FilterEnum.GT, FilterEnum.LE,
                                  FilterEnum.GE, FilterEnum.NE, FilterEnum.CONTAINS,
                                  FilterEnum.REGEXP, FilterEnum.STARTS])
    BOOL = Mapping(ValueBool, bool, [FilterEnum.EQ, FilterEnum.NE])
    INT = Mapping(ValueInt, int, [FilterEnum.EQ, FilterEnum.LT, FilterEnum.GT, FilterEnum.LE,
                                  FilterEnum.GE, FilterEnum.NE])
    FLOAT = Mapping(ValueFloat, float, [FilterEnum.EQ, FilterEnum.LT, FilterEnum.GT, FilterEnum.LE,
                                        FilterEnum.GE, FilterEnum.NE])
    FK = Mapping(ValueForeignKey, int)
    DT = Mapping(ValueDatetime, make_aware_datetime, [FilterEnum.EQ, FilterEnum.LT, FilterEnum.GT,
                                                      FilterEnum.LE, FilterEnum.GE, FilterEnum.NE])
    DATE = Mapping(ValueDate, lambda x: x, [FilterEnum.EQ, FilterEnum.LT, FilterEnum.GT,
                                            FilterEnum.LE, FilterEnum.GE, FilterEnum.NE])


class Schema(Base):
    __tablename__ = 'schemas'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True)
    slug = Column(String(128), unique=True)
    deleted = Column(Boolean, default=False)
    reviewable = Column(Boolean, default=False)

    entities = relationship('Entity', back_populates='schema')
    attr_defs = relationship('AttributeDefinition', back_populates='schema',
                             foreign_keys="[AttributeDefinition.schema_id]")

    def __str__(self):
        return self.name


class Entity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False)
    schema_id = Column(Integer, ForeignKey('schemas.id'))
    deleted = Column(Boolean, default=False)

    schema = relationship('Schema', back_populates='entities')

    __table_args__ = (
        UniqueConstraint('slug', 'schema_id'),
    )

    def __str__(self):
        return self.name

    def get(self, attr_name: str, db: Session) -> Union[Optional[Value], List[Value]]:
        attr_def: AttributeDefinition = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == self.schema_id)
            .where(Attribute.name == attr_name)
            .join(Attribute, AttributeDefinition.attribute_id == Attribute.id)
        ).scalar()

        if attr_def is None:
            raise KeyError(f'There is no attribute named `{attr_name}` defined for schema id {self.schema_id}')

        attr: Attribute = attr_def.attribute
        val_model = attr.type.value.model
        q = select(val_model).where(val_model.attribute_id == attr.id).where(val_model.entity_id == self.id)
        if attr_def.list:
            return db.execute(q).scalars().all()
        else:
            return db.execute(q).scalar()


class Attribute(Base):
    __tablename__ = 'attributes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    type: AttrType = Column(Enum(AttrType))

    __table_args__ = (
        UniqueConstraint('name', 'type'),
    )

    attr_defs = relationship('AttributeDefinition', back_populates='attribute')


class AttributeDefinition(Base):
    __tablename__ = 'attr_definitions'

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey('schemas.id'))
    attribute_id = Column(Integer, ForeignKey('attributes.id'))
    required = Column(Boolean)
    unique = Column(Boolean)
    key = Column(Boolean)
    list = Column(Boolean, default=False)
    description = Column(String(128))
    bound_schema_id = Column(Integer, ForeignKey('schemas.id'), nullable=True)

    schema = relationship('Schema', back_populates='attr_defs', foreign_keys=[schema_id])
    bound_schema = relationship('Schema', foreign_keys=[bound_schema_id])
    attribute = relationship('Attribute', back_populates='attr_defs')

    __table_args__ = (
        UniqueConstraint('schema_id', 'attribute_id'),
    )
