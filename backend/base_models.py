from typing import NamedTuple

from .database import Base

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship


class Value(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)

    @declared_attr
    def entity_id(cls):
        return Column(Integer, ForeignKey('entities.id'))

    @declared_attr
    def attribute_id(cls):
        return Column(Integer, ForeignKey('attributes.id'))

    @declared_attr
    def entity(cls):
        return relationship('Entity')


class Mapping(NamedTuple):
    model: Value
    converter: type
