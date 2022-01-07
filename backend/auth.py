from typing import Optional, List
from pydantic.fields import T

import sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.functions import func

from backend.exceptions import CircularGroupReferenceException, GroupExistsException, MissingGroupException, MissingGroupPermissionException, MissingPermissionException, MissingUserException, MissingUserGroupException, NoOpChangeException
from .config import settings as s
from datetime import datetime, timedelta
from fastapi import status, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from . import database
from .models import (
    User, 
    Permission, 
    GroupPermission, 
    UserGroup, Group, 
    UserPermission,
    PermObject,
    PermType
)
from .schemas.auth import (
    UserSchema, 
    PermissionSchema, 
    CreateGroupSchema, 
    UpdateGroupSchema,
    GroupSchema, 
    GroupDetailsSchema
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_users(db: Session) -> List[User]:
    return db.execute(select(User)).scalars().all()


def get_user(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user(db=db, username=username)
    if user is None:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, key=s.secret, algorithm=s.pwd_hash_alg)


def get_current_user(
    db: Session = Depends(database.get_db), 
    token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, s.secret, algorithms=[s.pwd_hash_alg])
        username = payload.get('sub')
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db=db, username=username)
    if user is None:
        raise credentials_exception
    return user


def _traverse_up_batch(groups: List[Group], perm: Permission, db: Session) -> bool:
    if not groups:
        return False
    match = db.execute(
        select(GroupPermission)
        .where(GroupPermission.group_id.in_([i.id for i in groups]))
        .where(GroupPermission.permission_id == perm.id)
    ).scalar()
    if match is not None:
        return True
    return _traverse_up_batch([i.parent for i in groups if i.parent_id is not None], perm, db)


def check_has_perm_in_groups(perm: Permission, user: User, db: Session) -> bool:
    groups = db.execute(
        select(Group)
        .join(UserGroup)
        .where(UserGroup.user_id == user.id)).scalars().all()
    return _traverse_up_batch(groups=groups, perm=perm, db=db)
    

def check_user_has_perm(user: User, perm: Permission, db: Session) -> bool:
    return bool(db.execute(
        select(UserPermission.id)
        .where(UserPermission.user_id == user.id)
        .where(UserPermission.permission_id == perm.id)
    ).scalar())


def is_authorized(
    perm_type: PermType, 
    perm_obj: PermObject,
    user: User,
    db: Session,
    obj_id: Optional[int] = None
) -> bool:
    perm = db.execute(
        select(Permission)
        .where(Permission.type == perm_type)
        .where(Permission.obj == perm_obj)
        .where(Permission.obj_id == obj_id)
    ).scalar()
    if perm is None:
        return False

    has_perm = check_user_has_perm(user=user, perm=perm, db=db)
    if has_perm:
        return True
    return check_has_perm_in_groups(perm=perm, user=user, db=db)


def get_groups(db: Session) -> List[Group]:
    return db.execute(select(Group)).scalars().all()


def get_group(group_id: int, db: Session) -> Optional[Group]:
    return db.execute(select(Group).where(Group.id == group_id)).scalar()


def get_group_or_raise(group_id: int, db: Session) -> Group:
    group = get_group(group_id=group_id, db=db)
    if group is None:
        raise MissingGroupException(obj_id=group_id)
    return group


def get_group_details(group_id: int, db: Session) -> GroupDetailsSchema:
    group = get_group_or_raise(group_id=group_id, db=db)
    member_count = db.execute(select(func.count(UserGroup.id)).where(UserGroup.group_id == group_id)).scalar()
    children = db.execute(select(Group).where(Group.parent_id == group.id)).scalars().all()
    perms = db.execute(
        select(Permission)
        .join(GroupPermission)
        .where(GroupPermission.group_id == group_id)
    ).scalars().all()
    return GroupDetailsSchema(**{**group.__dict__, 'children': children, 'permissions': perms, 'member_count': member_count})


def get_group_members(group_id: int, db: Session) -> List[User]:
    group = get_group_or_raise(group_id=group_id, db=db)
    users = db.execute(
        select(User)
        .join(UserGroup)
        .where(UserGroup.group_id == group.id)
    ).scalars().all()
    return users
    

def get_permission(data: PermissionSchema, db: Session) -> Optional[Permission]:
    return db.execute(
        select(Permission)
        .where(Permission.obj_id == data.obj_id)
        .where(Permission.obj == data.obj)
        .where(Permission.type == data.type)
    ).scalar()


def create_or_get_permission(data: PermissionSchema, db: Session, commit: bool = True) -> Permission:
    exists = get_permission(data=data, db=db)
    if exists:
        return exists
    perm = Permission(**data.dict())
    db.add(perm)
    if commit:
        db.commit()
    else:
        db.flush()
    return perm
 

def create_group(data: CreateGroupSchema, db: Session) -> Group:
    group = Group(name=data.name, parent_id=data.parent_id)
    db.add(group)
    try:
        db.flush()
    except sqlalchemy.exc.IntegrityError:
        raise GroupExistsException(name=data.name)

    for perm in data.permissions:
        perm = create_or_get_permission(data=perm, db=db, commit=False)
        db.add(GroupPermission(group=group, permission=perm))
    db.flush()

    for user_id in data.members:
        db.add(UserGroup(user_id=user_id, group=group))
    try:
        db.commit()
        return group
    except sqlalchemy.exc.IntegrityError as e:
        raise MissingUserException(obj_id=e.params['user_id'])


def get_user_by_id(user_id: int, db: Session) -> Optional[User]:
    return db.execute(select(User).where(User.id == user_id)).scalar()


def _check_no_op_changes(data: UpdateGroupSchema):
    perm_intersection = set(data.add_permissions).intersection(data.delete_permissions)
    if perm_intersection:
        raise NoOpChangeException('No-op change: made an attempt to add and delete the same permission')
    user_intersection = set(data.add_users).intersection(data.delete_users)
    if user_intersection:
        raise NoOpChangeException('No-op change: made an attempt to add and delete the same user from group')


def _is_circular_group_reference(child_id: int, parent_id: int, db: Session):
    while True:
        group = db.execute(select(Group).where(Group.id == parent_id)).scalar()
        if group.parent_id is None:
            break
        elif group.parent_id == child_id:
            return True
        else:
            parent_id = group.parent_id
    return False

def update_group(group_id: int, data: UpdateGroupSchema, db: Session) -> Group:
    group = get_group_or_raise(group_id=group_id, db=db)
    group.parent_id = data.parent_id or group.parent_id
    if data.parent_id:
        cycle = _is_circular_group_reference(child_id=group_id, parent_id=data.parent_id, db=db)
        if cycle:
            raise CircularGroupReferenceException

    group.name = data.name or group.name
    try:
        db.flush()
    except sqlalchemy.exc.IntegrityError:
        raise GroupExistsException(name=data.name)
    
    _check_no_op_changes(data=data)
    
    for perm in data.add_permissions:
        perm = create_or_get_permission(data=perm, db=db, commit=False)
        db.add(GroupPermission(group=group, permission=perm))
    for perm_ in data.delete_permissions:
        perm = get_permission(data=perm_, db=db)
        if perm is None:
            raise MissingPermissionException(obj_id=f'{perm_.type.name}:{perm_.obj.name}:{perm_.obj_id}')
        group_perm = db.execute(
            select(GroupPermission)
            .where(GroupPermission.group_id == group_id)
            .where(GroupPermission.permission_id == perm.id)
        ).scalar()
        if group_perm is None:
            raise MissingGroupPermissionException(obj_id=f'G{group_id}:P{perm.id}')
        db.delete(group_perm)
    db.flush()
    
    for user_id in data.add_users:
        user = get_user_by_id(user_id=user_id, db=db)
        if user is None:
            raise MissingUserException(obj_id=user_id)
        db.add(UserGroup(user_id=user_id, group_id=group.id))

    for user_id in data.delete_users:
        user = get_user_by_id(user_id=user_id, db=db)
        if user is None:
            raise MissingUserException(obj_id=user_id)
        user_group = db.execute(
            select(UserGroup)
            .where(UserGroup.user_id == user_id)
            .where(UserGroup.group_id == group.id)
        ).scalar()
        if user_group is None:
            raise MissingUserGroupException(obj_id=f'U{user_id}:G{group.id}')
        db.delete(user_group)
    db.commit()
    return group