from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql.schema import UniqueConstraint

from ..base_models import Base
from .enum import RecipientType, PermissionTargetType, PermissionType

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
