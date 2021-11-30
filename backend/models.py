import enum
from typing import List, Union, Optional, NamedTuple

from sqlalchemy import (
    select, Enum, DateTime, Date,
    Boolean, Column, ForeignKey, 
    Integer, String, Float)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.schema import UniqueConstraint

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


class AttrType(enum.Enum):
    STR = Mapping(ValueStr, str)
    BOOL = Mapping(ValueBool, bool)
    INT = Mapping(ValueInt, int)
    FLOAT = Mapping(ValueFloat, float)
    FK = Mapping(ValueForeignKey, int)
    DT = Mapping(ValueDatetime, lambda x: x)
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


# class Group(Base):
#     __tablename__ = 'groups'

#     id = Column(Integer, primary_key=True)
#     name = Column(String(128), nullable=False)
#     parent_id = Column(Integer, ForeignKey('groups.id'))
#     parent = relationship('Group', remote_side=[id], backref=backref('subgroups'))


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    password = Column(String, nullable=False)

# class PermObject(enum.Enum):
#     SCHEMA = 'SCHEMA'
#     ENTITY = 'ENTITY'

# class PermType(enum.Enum):
#     CREATE = 'CREATE'
#     UPDATE = 'UPDATE'
#     DELETE = 'DELETE'

#     CREATE_ENTITIES = 'CREATE_ENTITIES'
#     UPDATE_ENTITIES = 'UPDATE_ENTITIES'
#     DELETE_ENTITIES = 'DELETE_ENTITIES'


# class Permission(Base):
#     __tablename__ = 'permissions'
#     id = Column(Integer, primary_key=True)
#     obj_id = Column(Integer)
#     obj_type = Column(Enum(PermObject), nullable=False)
#     name = Column(Enum(PermType), nullable=False)


# class GroupPermission(Base):
#     __tablename__ = 'group_permissions'
#     id = Column(Integer, primary_key=True)
#     group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
#     permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)

#     group = relationship('Group')
#     permission = relationship('Permission')

#     __table_args__ = (
#         UniqueConstraint('group_id', 'permission_id'),
#     )


# class UserPermission(Base):
#     __tablename__ = 'user_permissions'
#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     permission_id = Column(Integer, ForeignKey('permissions.id'), nullable=False)

#     user = relationship('User')
#     permission = relationship('Permission')

#     __table_args__ = (
#         UniqueConstraint('user_id', 'permission_id'),
#     )


# class UserGroup(Base):
#     __tablename__ = 'user_groups'
#     id = Column(Integer, primary_key=True)
#     group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
#     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

#     group = relationship('Group')
#     user = relationship('User')

#     __table_args__ = (
#         UniqueConstraint('user_id', 'group_id'),
#     )

class ChangeStatus(enum.Enum):
    PENDING = 'PENDING'
    DECLINED = 'DECLINED'
    APPROVED = 'APPROVED'


class ChangeObject(enum.Enum):
    SCHEMA = 'SCHEMA'
    ENTITY = 'ENTITY'

class ChangeType(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ChangeStatus), default=ChangeStatus.PENDING, nullable=False)
    change_object = Column(Enum(ChangeObject), nullable=False)
    change_type = Column(Enum(ChangeType), nullable=False)
    comment = Column(String(1024), nullable=True)

    created_by = relationship('User', foreign_keys=[created_by_user_id])
    reviewed_by = relationship('User', foreign_keys=[reviewed_by_user_id])
    

class SchemaCreate(Base):
    __tablename__ = 'schema_create_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False)
    reviewable = Column(Boolean, nullable=False)

    change = relationship('Change')


class SchemaUpdate(Base):
    __tablename__ = 'schema_upd_history'
    id = Column(Integer, primary_key=True) 
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    schema_id = Column(Integer, ForeignKey('schemas.id'), nullable=False)
    new_name = Column(String(128), nullable=True)
    old_name = Column(String(128), nullable=True)
    new_slug = Column(String(128), nullable=True)
    old_slug = Column(String(128), nullable=True)
    new_reviewable = Column(Boolean, nullable=True)
    old_reviewable = Column(Boolean, nullable=True)
    new_deleted = Column(Boolean, nullable=True)
    old_deleted = Column(Boolean, nullable=True)

    change = relationship('Change')
    schema = relationship('Schema')


class AttributeUpdate(Base):
    __tablename__ = 'attr_upd_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    attribute_id = Column(Integer, ForeignKey('attributes.id'), nullable=False)
    new_name = Column(String(128), nullable=True)
    required = Column(Boolean, nullable=False)
    unique = Column(Boolean, nullable=False)
    list = Column(Boolean, nullable=False)
    key = Column(Boolean, nullable=False)
    description = Column(String(128), nullable=True)
    bind_to_schema = Column(Integer, ForeignKey('schemas.id'), nullable=True)

    change = relationship('Change')
    attribute = relationship('Attribute')


class AttributeCreate(Base):
    __tablename__ = 'attr_create_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    name = Column(String(128), nullable=False)
    type = Column(Enum(AttrType), nullable=False)
    required = Column(Boolean, nullable=False)
    unique = Column(Boolean, nullable=False)
    list = Column(Boolean, nullable=False)
    key = Column(Boolean, nullable=False)
    description = Column(String(128), nullable=True)
    bind_to_schema = Column(Integer, ForeignKey('schemas.id'), nullable=True)

    change = relationship('Change')


class AttributeDelete(Base):
    __tablename__ = 'attr_delete_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    attribute_id = Column(Integer, ForeignKey('attributes.id'), nullable=False)

    change = relationship('Change')
    attribute = relationship('Attribute')


class EntityCreate(Base):
    __tablename__ = 'entity_create_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    schema_id = Column(Integer, ForeignKey('schemas.id'), nullable=False)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False)

    change = relationship('Change')
    schema = relationship('Schema')


class EntityUpdate(Base):
    __tablename__ = 'entity_update_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    new_name = Column(String(128), nullable=True)
    new_slug = Column(String(128), nullable=True)
    old_name = Column(String(128), nullable=True)
    old_slug = Column(String(128), nullable=True)
    new_deleted = Column(Boolean, nullable=True)
    old_deleted = Column(Boolean, nullable=True)

    change = relationship('Change')
    entity = relationship('Entity')


class ValueUpdate(Base):
    __tablename__ = 'value_update_history'
    id = Column(Integer, primary_key=True)
    change_id = Column(Integer, ForeignKey('changes.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('entities.id'))
    attribute_id = Column(Integer, ForeignKey('attributes.id'), nullable=False)
    new_value = Column(String, nullable=True)
    old_value = Column(String, nullable=True) 

    change = relationship('Change')
    entity = relationship('Entity')
    attribute = relationship('Attribute')