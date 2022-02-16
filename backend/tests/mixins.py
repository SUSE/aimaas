import typing

from sqlalchemy.orm import Session

from ..auth.crud import create_group, create_user
from ..auth.models import User, Group
from ..schemas.auth import BaseGroupSchema, UserCreateSchema


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
