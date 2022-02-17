import typing

from sqlalchemy.orm import Session

from ..auth.crud import create_group, create_user, add_members, grant_permission
from ..auth.enum import RecipientType, PermissionTargetType, PermissionType
from ..auth.models import User, Group
from ..schemas.auth import BaseGroupSchema, UserCreateSchema, PermissionSchema


class CreateMixin:
    default_username = "testuser-0"
    default_password = "secret"
    default_groupname = "test"

    def _create_group(self, dbsession: Session, data: typing.Optional[BaseGroupSchema] = None) \
            -> Group:
        data = data or BaseGroupSchema(name=self.default_groupname, parent_id=None)
        return create_group(db=dbsession, data=data)

    def _create_user(self, dbsession: Session, data: typing.Optional[UserCreateSchema] = None) \
            -> User:
        data = data or UserCreateSchema(username=self.default_username,
                                        password=self.default_password,
                                        email="t@example.org")
        return create_user(dbsession, data)

    def _grant_permission(self, dbsession: Session, data: typing.Optional[PermissionSchema] = None)\
            -> bool:
        if not data:
            user = self._create_user(dbsession)
            data = PermissionSchema(recipient_type=RecipientType.USER, recipient_name=user.username,
                                    obj_type=PermissionTargetType.ENTITY, obj_id=1,
                                    permission=PermissionType.UPDATE_ENTITY)
        return grant_permission(data, dbsession)

    def _create_user_group_with_perm(self, dbsession: Session) -> typing.Tuple[User, Group, Group]:
        pgroup = self._create_group(dbsession)
        group = self._create_group(dbsession, BaseGroupSchema(name="subgroup", parent_id=pgroup.id))
        user = self._create_user(dbsession)
        add_members(group.id, [user.id], dbsession)

        # Grant permission to user
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.USER, recipient_name=user.username,
            obj_type=PermissionTargetType.ENTITY, obj_id=1,
            permission=PermissionType.DELETE_ENTITY))

        # Grant permission to parent group
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.GROUP, recipient_name=pgroup.name,
            obj_type=PermissionTargetType.SCHEMA, obj_id=1,
            permission=PermissionType.READ_ENTITY))

        # Grant permission to group
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.GROUP, recipient_name=group.name,
            obj_type=PermissionTargetType.SCHEMA, obj_id=1,
            permission=PermissionType.UPDATE_ENTITY))

        return user, group, pgroup
