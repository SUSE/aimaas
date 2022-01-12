from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ..auth.enum import PermissionType, RecipientType, PermissionTargetType
from ..database import Base


class Token(BaseModel):
    access_token: str
    token_type: str
    expiration_date: datetime


class BaseUserSchema(BaseModel):
    username: str
    email: str


class UserIDSchema(BaseModel):
    id: int


class UserNameMixin(BaseModel):
    firstname: Optional[str]
    lastname: Optional[str]


class UserSchema(UserIDSchema, UserNameMixin, BaseUserSchema):
    is_active: bool

    class Config:
        orm_mode = True


class UserCreateSchema(UserNameMixin, BaseUserSchema):
    password: Optional[str]


class RequirePermission(BaseModel):
    permission: PermissionType
    target: Optional[Base]

    class Config:
        arbitrary_types_allowed = True


class PermissionSchema(BaseModel):
    recipient_type: RecipientType
    recipient_name: str
    obj_type: Optional[PermissionTargetType]
    obj_id: Optional[int]
    permission: PermissionType

    def __str__(self) -> str:
        return ":".join(str(x or "") for x in (self.permission, self.obj_type, self.obj_id,
                                               self.recipient_type, self.recipient_name))

    def __hash__(self) -> int:
        return hash(str(self))

    class Config:
        orm_mode = True


class PermissionWithIdSchema(PermissionSchema):
    id: int

    class Config:
        orm_mode = True


class BaseGroupSchema(BaseModel):
    name: str
    parent_id: Optional[int]


class GroupSchema(BaseGroupSchema):
    id: int

    class Config:
        orm_mode = True
