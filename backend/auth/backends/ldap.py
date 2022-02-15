from functools import cached_property
from typing import Optional, Any

from ldap3 import Server, Connection, LEVEL, ALL_ATTRIBUTES, SYNC, Entry

from ...config import settings
from ...schemas.auth import UserCreateSchema
from ..crud import get_or_create_user
from ..models import User
from .abstract import AbstractBackend


class Backend(AbstractBackend):
    _server = Server(host=settings.ldap.host, connect_timeout=settings.ldap.timeout)

    @staticmethod
    def search_string(username: str) -> str:
        return settings.ldap.search_template.format(username=username)

    @staticmethod
    def bind_user(username: str) -> str:
        return settings.ldap.bind_template.format(username=username)

    @cached_property
    def connection(self) -> Connection:
        return Connection(
            server=self._server,
            user=settings.ldap.user,
            password=settings.ldap.password,
            read_only=True,
            receive_timeout=settings.ldap.timeout,
            client_strategy=SYNC,
        )

    @staticmethod
    def get_attr_value(entry: Entry, attribute_name: str, default: Optional[str] = None) -> Any:
        attr = getattr(entry, attribute_name, None)
        return attr.value if attr else default

    def get_user_data(self, username: str) -> Optional[UserCreateSchema]:
        with self.connection as conn:
            conn.search(
                search_base='cn=users,dc=suse,dc=de',
                search_scope=LEVEL,
                search_filter=self.search_string(username=username),
                attributes=ALL_ATTRIBUTES
            )
            if not conn.entries:
                return None

            params = {field: self.get_attr_value(entry=conn.entries[0], attribute_name=attr)
                      for field, attr in settings.ldap.attr.dict().items()}

            return UserCreateSchema(password="", **params)

    def get_user(self, user_data: UserCreateSchema) -> Optional[User]:
        user, _ = get_or_create_user(db=self.db, data=user_data)
        return user

    def check_password(self, username: str, password: str) -> bool:
        with self.connection as conn:
            return conn.rebind(user=self.bind_user(username=username), password=password)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user_data = self.get_user_data(username=username)
        if not user_data:
            return None

        if not self.check_password(username=username, password=password):
            return None

        return self.get_user(user_data=user_data)
