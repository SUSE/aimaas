from abc import ABC, abstractmethod
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm.session import Session

from ..models import User


class AbstractBackend(ABC):
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[User]:
        return NotImplemented
