from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum, text
from sqlalchemy.event import listens_for
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import UniqueConstraint

from .enum import RecipientType, PermissionTargetType, PermissionType
from ..base_models import Base


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('groups.id', ondelete="RESTRICT"))

    parent = relationship('Group', remote_side=[id], back_populates='subgroups')
    subgroups = relationship('Group', back_populates="parent", passive_deletes='all')
    members = relationship('UserGroup', back_populates="group", cascade="delete")

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

    groups = relationship('UserGroup', back_populates="user", cascade="delete")

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

    @property
    def recipient(self):
        return self.user if self.recipient_type == RecipientType.USER else self.group

    @property
    def object(self):
        if self.obj_type == PermissionTargetType.ENTITY:
            return self.entity
        if self.obj_type == PermissionTargetType.SCHEMA:
            return self.schema
        return self.managed_group


class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

    group = relationship('Group', back_populates="members")
    user = relationship('User', back_populates="groups")

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id'),
    )


def delete_dangling_permissions(connection, recipient_type: RecipientType, recipient_id: int):
    connection.execute(
        text("DELETE FROM permissions WHERE recipient_type = :type AND recipient_id = :id"),
        {"type": recipient_type.name, "id": recipient_id}
    )


# Since permissions table doesn't relate to its recipient tables we can't use sqlalchemy's cascade
# setting, but we have to delete those manually using event listeners.
@listens_for(User, "after_delete")
def delete_dangling_user_permissions(_, connection, target):
    delete_dangling_permissions(connection, RecipientType.USER, target.id)


@listens_for(Group, "after_delete")
def delete_dangling_group_permissions(_, connection, target):
    delete_dangling_permissions(connection, RecipientType.GROUP, target.id)
