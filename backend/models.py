import enum
from datetime import datetime
from typing import List, Union, Optional, NamedTuple

from sqlalchemy import (
    select, Enum, DateTime,
    Boolean, Column, ForeignKey,
    Integer, String, Float)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.schema import UniqueConstraint

from .auth.enum import PermissionType, PermissionTargetType, RecipientType
from .config import settings
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

    @declared_attr
    def entity(cls):
        return relationship('Entity')


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


class Mapping(NamedTuple):
    model: Value
    converter: type


def make_aware_datetime(dt: datetime) -> datetime:
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=settings.timezone)
    return dt


class AttrType(enum.Enum):
    STR = Mapping(ValueStr, str)
    BOOL = Mapping(ValueBool, bool)
    INT = Mapping(ValueInt, int)
    FLOAT = Mapping(ValueFloat, float)
    FK = Mapping(ValueForeignKey, int)
    DT = Mapping(ValueDatetime, make_aware_datetime)


class BoundFK(Base):
    __tablename__ = 'bound_foreign_keys'

    id = Column(Integer, primary_key=True, index=True)
    attr_def_id = Column(Integer, ForeignKey('attr_definitions.id'))
    schema_id = Column(Integer, ForeignKey('schemas.id'))

    attr_def = relationship('AttributeDefinition')
    schema = relationship(
        'Schema',
        doc='''Points to schema that is bound 
            to BoundFK.attr_def which is 
            not necessarily the same as 
            BoundFK.attr_def.schema'''
    )


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
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False)
    schema_id = Column(Integer, ForeignKey('schemas.id'))
    deleted = Column(Boolean, default=False)

    schema = relationship('Schema', back_populates='entities')

    __table_args__ = (
        UniqueConstraint('slug', 'schema_id'),
    )

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
    description = Column(String)

    schema = relationship('Schema', back_populates='attr_defs')
    attribute = relationship('Attribute', back_populates='attr_defs')

    __table_args__ = (
        UniqueConstraint('schema_id', 'attribute_id'),
    )


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('groups.id'))
    parent = relationship('Group', remote_side=[id], backref=backref('subgroups'))

    def __str__(self):
        return self.name


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    password = Column(String, nullable=True)
    firstname = Column(String(128), nullable=True)
    lastname = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)

    def __str__(self):
        return self.username


class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    recipient_type = Column(Enum(RecipientType), nullable=False)
    recipient_id = Column(Integer, nullable=False)
    obj_type = Column(Enum(PermissionTargetType), nullable=True)
    obj_id = Column(Integer, nullable=True)
    permission = Column(Enum(PermissionType), nullable=False)

    user = relationship('User',
                        primaryjoin="and_(User.id == foreign(Permission.recipient_id), "
                                    "Permission.recipient_type == 'USER')",
                        overlaps="group")
    group = relationship('Group',
                         primaryjoin="and_(Group.id == foreign(Permission.recipient_id), "
                                     "Permission.recipient_type == 'GROUP')",
                         overlaps="user")
    schema = relationship('Schema',
                          primaryjoin="and_(Schema.id == foreign(Permission.obj_id), "
                                      "Permission.obj_type == 'SCHEMA')",
                          overlaps="entity, managed_group"
                          )
    entity = relationship('Entity',
                          primaryjoin="and_(Entity.id == foreign(Permission.obj_id), "
                                      "Permission.obj_type == 'ENTITY')",
                          overlaps="schema, managed_group"
                          )
    managed_group = relationship('Group',
                                 primaryjoin="and_(Group.id == foreign(Permission.obj_id), "
                                             "Permission.obj_type == 'GROUP')",
                                 overlaps="schema, entity"
                                 )

    __table_args__ = (
        UniqueConstraint('recipient_type', 'recipient_id', 'obj_type', 'obj_id', 'permission'),
    )

    @property
    def recipient_name(self):
        return self.user.username if self.recipient_type == RecipientType.USER else self.group.name


class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    group = relationship('Group')
    user = relationship('User')

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id'),
    )
