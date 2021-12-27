from typing import List, Optional

from pydantic import BaseModel

from ..models import PermType, PermObject


class Token(BaseModel):
    access_token: str
    token_type: str


class UserSchema(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True


class UserCreateSchema(BaseModel):
    email: str
    username: str
    password: str


class PermissionSchema(BaseModel):
    obj_id: Optional[int]
    obj: PermObject
    type: PermType

    def __hash__(self) -> int:
        return hash(f'{self.obj_id}${self.obj.name}${self.type.name}')

    class Config:
        orm_mode = True


class GroupSchema(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]

    class Config:
        orm_mode = True


class GroupDetailsSchema(BaseModel):
    id: int
    name: str
    children: List[GroupSchema]
    permissions: List[PermissionSchema]
    member_count: int


class CreateGroupSchema(BaseModel):
    name: str
    parent_id: Optional[int]
    permissions: List[PermissionSchema]
    members: List[int] 


class UpdateGroupSchema(BaseModel):
    name: Optional[str]
    parent_id: Optional[int]
    add_permissions: List[PermissionSchema] = []
    delete_permissions: List[PermissionSchema] = []
    add_users: List[int] = []
    delete_users: List[int] = []