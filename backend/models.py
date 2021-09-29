import enum
from datetime import datetime
from typing import List, Union, Optional

from sqlalchemy import (
    select, Enum, DateTime,
    Boolean, Column, ForeignKey, 
    Integer, String, Float)
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declared_attr

from .database import Base

class Value(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    @declared_attr
    def entity_id(cls):
        return Column(Integer, ForeignKey('entities.id'))

    @declared_attr
    def attribute_id(cls):
        return Column(Integer, ForeignKey('attributes.id'))


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
    value = Column(DateTime)


class AttrType(enum.Enum):
    str = 'str'
    bool = 'bool'
    int = 'int'
    float = 'float'
    fk = 'fk'
    dt = 'dt'


val_map = {
    AttrType.str: ValueStr,
    AttrType.bool: ValueBool,
    AttrType.int: ValueInt,
    AttrType.float: ValueFloat,
    AttrType.fk: ValueForeignKey,
    AttrType.dt: ValueDatetime
}


type_map = {
    AttrType.str: str,
    AttrType.bool: bool,
    AttrType.int: int,
    AttrType.float: float,
    AttrType.fk: int,
    AttrType.dt: datetime
}


class BoundFK(Base):
    __tablename__ = 'bound_foreign_keys'

    id = Column(Integer, primary_key=True, index=True)
    attr_def_id = Column(Integer, ForeignKey('attr_definitions.id'))
    schema_id = Column(Integer, ForeignKey('schemas.id'))

    attr_def = relationship('AttributeDefinition')
    schema = relationship('Schema')


class Schema(Base):
    __tablename__ = 'schemas'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True)
    slug = Column(String(128), unique=True)
    deleted = Column(Boolean, default=False)

    entities = relationship('Entity', back_populates='schema')
    attr_defs = relationship('AttributeDefinition', back_populates='schema')
    

class Entity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, index=True)
    schema_id = Column(Integer, ForeignKey('schemas.id'))
    deleted = Column(Boolean, default=False)

    schema = relationship('Schema', back_populates='entities')

    def get(self, attr_name: str, db: Session) -> Union[Optional[Value], List[Value]]:
        attr = db.execute(select(Attribute).where(Attribute.name == attr_name)).scalar()
        if attr is None:
            raise KeyError(f'There is no attribute named `{attr_name}`')
        
        attr_def = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == self.schema_id)
            .where(AttributeDefinition.attribute_id == attr.id)
        ).scalar()
        if attr_def is None:
            raise KeyError(f'There is no attribute named `{attr_name}` defined for schema id {self.schema_id}')

        val_model = val_map[AttrType(attr.type)]
        q = select(val_model).where(val_model.attribute_id == attr.id).where(val_model.entity_id == self.id)
        if attr_def.list:
            return db.execute(q).scalars().all()
        else:
            return db.execute(q).scalar()


class Attribute(Base):
    __tablename__ = 'attributes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True)
    type = Column(Enum(AttrType))

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
    description = Column(String)

    schema = relationship('Schema', back_populates='attr_defs')
    attribute = relationship('Attribute', back_populates='attr_defs')