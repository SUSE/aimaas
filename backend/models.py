import enum
from typing import List, Union, Optional, NamedTuple
from datetime import datetime

from sqlalchemy import (
    select, Enum, DateTime, Date,
    Boolean, Column, ForeignKey, 
    Integer, String, Float)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.schema import CheckConstraint, UniqueConstraint

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

class ValueDate(Value):
    __tablename__ = 'values_date'
    value = Column(Date)

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
    DATE = Mapping(ValueDate, lambda x: x)


class BoundFK(Base):
    __tablename__ = 'bound_foreign_keys'

    id = Column(Integer, primary_key=True, index=True)
    attr_def_id = Column(Integer, ForeignKey('attr_definitions.id'))
    schema_id = Column(Integer, ForeignKey('schemas.id'))

    attr_def = relationship(
        'AttributeDefinition', 
        back_populates='bound_fk')
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
    reviewable = Column(Boolean, default=False)

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
    description = Column(String(128))

    schema = relationship('Schema', back_populates='attr_defs')
    attribute = relationship('Attribute', back_populates='attr_defs')
    bound_fk = relationship('BoundFK', back_populates='attr_def', uselist=False)

    __table_args__ = (
        UniqueConstraint('schema_id', 'attribute_id'),
    )


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    parent_id = Column(Integer, ForeignKey('groups.id'))
    parent = relationship('Group', remote_side=[id], backref=backref('subgroups'))


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    password = Column(String, nullable=False)


class PermObject(enum.Enum):
    SCHEMA = 'SCHEMA'
    ENTITY = 'ENTITY'


class PermType(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    READ = 'READ'

    CREATE_ENTITIES = 'CREATE_ENTITIES'
    UPDATE_ENTITIES = 'UPDATE_ENTITIES'
    DELETE_ENTITIES = 'DELETE_ENTITIES'


class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    obj_id = Column(Integer)
    obj = Column(Enum(PermObject), nullable=False)
    type = Column(Enum(PermType), nullable=False)


class GroupPermission(Base):
    __tablename__ = 'group_permissions'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)

    group = relationship('Group')
    permission = relationship('Permission')

    __table_args__ = (
        UniqueConstraint('group_id', 'permission_id'),
    )


class UserPermission(Base):
    __tablename__ = 'user_permissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)

    user = relationship('User')
    permission = relationship('Permission')

    __table_args__ = (
        UniqueConstraint('user_id', 'permission_id'),
    )


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

#################### TRACEABILITY #########################
class ChangeObject(enum.Enum):
    SCHEMA = 'SCHEMA'
    ENTITY = 'ENTITY'


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


class ChangeStatus(enum.Enum):
    PENDING = 'PENDING'
    DECLINED = 'DECLINED'
    APPROVED = 'APPROVED'


class ChangeType(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'


class ChangeRequest(Base):
    __tablename__ = 'change_requests'
    id = Column(Integer, primary_key=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey('users.id'))
    
    created_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ChangeStatus), default=ChangeStatus.PENDING, nullable=False)
    comment = Column(String(1024), nullable=True)

    created_by = relationship('User', foreign_keys=[created_by_user_id])
    reviewed_by = relationship('User', foreign_keys=[reviewed_by_user_id])


class ContentType(enum.Enum):
    ATTRIBUTE = 'ATTRIBUTE'
    ATTRIBUTE_DEFINITION = 'ATTRIBUTE_DEFINITION'
    ENTITY = 'ENTITY'
    SCHEMA = 'SCHEMA'


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