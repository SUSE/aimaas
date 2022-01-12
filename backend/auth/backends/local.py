from typing import Optional

from .abstract import AbstractBackend
from ..context import pwd_context
from ..crud import get_user
from ...models import User


class Backend(AbstractBackend):
    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = get_user(db=self.db, username=username)
        if user is None:
            return None
        if not pwd_context.verify(password, user.password):
            return None
        return user
