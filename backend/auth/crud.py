import typing
from typing import List, Optional, Tuple

import sqlalchemy
from sqlalchemy import select, literal, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import STATEMENTS
from .. import exceptions
from ..models import Schema, Entity
from .models import User, Group, Permission, UserGroup
from ..schemas.auth import BaseGroupSchema, PermissionSchema, GroupSchema, \
    UserCreateSchema, RequirePermission, PermissionWithIdSchema
from .context import get_password_hash
from .enum import PermissionType, PermissionTargetType, RecipientType


def _is_circular_group_reference(child_id: int, parent_id: int, db: Session) -> None:
    all_parent_ids = [x[0] for x in db.execute(STATEMENTS.all_parent_groups,
                                               {"groupids": [parent_id]})]
    if child_id in all_parent_ids:
        raise exceptions.CircularGroupReferenceException()


def get_users(db: Session, user_ids: typing.Optional[typing.List[int]] = None) -> List[User]:
    users = db.query(User)

    if user_ids:
        users = users.filter(User.id.in_(user_ids))
        missing_user_ids = set(user_ids) - {u.id for u in users}
        if missing_user_ids:
            raise exceptions.MissingUserException(obj_id=next(iter(missing_user_ids)))

    return users


def get_user(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar()


def create_user(db: Session, data: UserCreateSchema) -> User:
    datadict = data.dict()
    if datadict.get("password"):
        datadict["password"] = get_password_hash(datadict["password"])

    user = User(**datadict)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(db: Session, data: UserCreateSchema) -> Tuple[User, bool]:
    user = get_user(db=db, username=data.username)
    if user:
        return user, False

    return create_user(db=db, data=data), True


def get_user_by_id(user_id: int, db: Session) -> Optional[User]:
    return db.execute(select(User).where(User.id == user_id)).scalar()


def activate_user(db: Session, user_id: Optional[int] = None,
                  username: Optional[str] = None) -> bool:
    if not user_id and not username:
        raise ValueError("`user_id` or `username` must be specified.")

    user = get_user(db=db, username=username) if username else get_user_by_id(user_id=user_id,
                                                                              db=db)
    if not user:
        raise exceptions.MissingUserException(user_id or username)

    if user.is_active:
        return False

    user.is_active = True
    db.commit()
    return True


def deactivate_user(db: Session, user_id: Optional[int] = None,
                    username: Optional[str] = None) -> bool:
    if not user_id and not username:
        raise ValueError("`user_id` or `username` must be specified.")

    user = get_user(db=db, username=username) if username else get_user_by_id(user_id=user_id,
                                                                              db=db)
    if not user:
        raise exceptions.MissingUserException(user_id or username)

    if not user.is_active:
        return False

    user.is_active = False
    db.commit()
    return True


def get_user_groups(db: Session, user: User) -> List[Group]:
    return db.query(Group).join(UserGroup).filter(UserGroup.user_id == user.id).all()


def get_groups(db: Session) -> List[Group]:
    return db.execute(select(Group)).scalars().all()


def get_group(group_id: int, db: Session) -> Optional[Group]:
    return db.execute(select(Group).where(Group.id == group_id)).scalar()


def get_group_or_raise(group_id: int, db: Session) -> Group:
    group = get_group(group_id=group_id, db=db)
    if group is None:
        raise exceptions.MissingGroupException(obj_id=group_id)
    return group


def get_group_details(group_id: int, db: Session) -> GroupSchema:
    group = get_group_or_raise(group_id=group_id, db=db)
    return GroupSchema(**group.__dict__)


def get_group_members(group_id: int, db: Session) -> List[User]:
    group = get_group_or_raise(group_id=group_id, db=db)
    return [assoc.user for assoc in group.members]


def create_group(data: BaseGroupSchema, db: Session) -> Group:
    group = Group(name=data.name, parent_id=data.parent_id)
    db.add(group)
    try:
        db.commit()
    except IntegrityError as error:
        raise exceptions.GroupExistsException(name=data.name) from error

    db.refresh(group)
    return group


def update_group(group_id: int, data: BaseGroupSchema, db: Session) -> [Group, bool]:
    group = get_group_or_raise(group_id=group_id, db=db)
    has_changed = False
    if data.parent_id and data.parent_id != group.parent_id:
        _is_circular_group_reference(child_id=group_id, parent_id=data.parent_id, db=db)
        group.parent_id = data.parent_id
        has_changed = True

    if data.name and data.name != group.name:
        group.name = data.name
        has_changed = True

    if has_changed:
        try:
            db.commit()
        except IntegrityError as error:
            raise exceptions.GroupExistsException(name=data.name) from error

    return group, has_changed


def add_members(group_id: int, user_ids: List[int], db: Session) -> bool:
    group = get_group_or_raise(group_id=group_id, db=db)
    users = get_users(db=db, user_ids=user_ids)

    already_members = get_group_members(group_id=group_id, db=db)
    was_added = False

    for user in users:
        if user in already_members:
            continue
        db.add(UserGroup(user_id=user.id, group_id=group.id))
        was_added = True

    if was_added:
        db.commit()

    return was_added


def delete_members(group_id: int, user_ids: List[int], db: Session) -> bool:
    # Check for existence of group
    get_group_or_raise(group_id=group_id, db=db)
    if not user_ids:
        return False

    # Check for existence of users
    get_users(db=db, user_ids=user_ids)
    count = db.query(UserGroup)\
        .filter(UserGroup.group_id == group_id, UserGroup.user_id.in_(user_ids))\
        .delete()
    db.commit()
    if count < 1:
        raise exceptions.MissingUserGroupException(user_id=user_ids[0], group_id=group_id)
    return count > 0


def has_permission(user: User, permission: RequirePermission, db: Session) -> bool:
    base_u = db.query(Permission.id)\
        .join(Permission.user)\
        .filter(Permission.user.property.mapper.class_.id == user.id)
    is_superuser = base_u.filter(Permission.permission == PermissionType.SUPERUSER)
    has_user_perm = base_u.filter(Permission.permission == permission.permission)

    user_groups = [x[0] for x in db.query(UserGroup.group_id).filter(UserGroup.user_id == user.id).all()]
    all_group_ids = [x[0] for x in db.execute(STATEMENTS.all_parent_groups, {"groupids": user_groups})]
    has_group_perm = db.query(Permission.id)\
        .join(Permission.group)\
        .filter(Permission.group.property.mapper.class_.id.in_(all_group_ids),
                Permission.permission == permission.permission)

    if isinstance(permission.target, Group):
        q = or_(Permission.obj_id == None,
                and_(Permission.obj_type == PermissionTargetType.GROUP,
                     Permission.obj_id == permission.target.id))
    elif isinstance(permission.target, Schema):
        q = or_(Permission.obj_id == None,
                and_(Permission.obj_type == PermissionTargetType.SCHEMA,
                     Permission.obj_id == permission.target.id))
    elif isinstance(permission.target, Entity):
        q = or_(Permission.obj_id == None,
                and_(Permission.obj_type == PermissionTargetType.ENTITY,
                     Permission.obj_id == permission.target.id))
        schema_id = permission.target.schema_id or db.query(Entity.schema_id)\
                                                     .filter(Entity.id == permission.target.id)\
                                                     .scalar()
        q = or_(q, and_(Permission.obj_type == PermissionTargetType.SCHEMA,
                        Permission.obj_id == schema_id),)
    elif permission.target is None:
        q = Permission.obj_id == None
    else:
        raise TypeError(f"Permission management for type {type(permission.target)} "
                        f"not supported")

    has_user_perm = has_user_perm.filter(q)
    has_group_perm = has_group_perm.filter(q)

    return db.query(literal(True))\
        .filter(is_superuser.union(has_user_perm, has_group_perm).exists())\
        .scalar() or False


def get_permissions(db: Session, recipient_type: Optional[RecipientType] = None,
                    recipient_id: Optional[int] = None,
                    obj_type: Optional[PermissionTargetType] = None,
                    obj_id: Optional[int] = None) -> List[PermissionWithIdSchema]:
    if (not recipient_type and recipient_id) or (recipient_type and not recipient_id):
        raise ValueError("Recipient type and ID must be specified as pair.")
    if (not obj_type and obj_id) or (obj_type and not obj_id):
        raise ValueError("Target/Object type and ID must be specified as pair.")

    query = db.query(Permission)

    if recipient_type:
        query = query.filter(Permission.recipient_type == recipient_type,
                             Permission.recipient_id == recipient_id)
        if recipient_type == RecipientType.USER:
            group_ids = [x[0] for x in db.query(UserGroup.group_id)
                                         .filter(UserGroup.user_id == recipient_id).all()]
        else:
            group_ids = [recipient_id]

        q = db.execute(STATEMENTS.all_parent_groups, {"groupids": group_ids})
        all_group_ids = [x[0] for x in q.fetchall()]
        subq = db.query(Permission).filter(Permission.recipient_type == RecipientType.GROUP,
                                           Permission.recipient_id.in_(all_group_ids))
        query = query.union(subq)
    if obj_type:
        query = query.filter(Permission.obj_type == obj_type, Permission.obj_id == obj_id)
        if obj_type == PermissionTargetType.ENTITY:
            schema_id = db.query(Entity.schema_id).filter(Entity.id == obj_id).one()
            subq = db.query(Permission)\
                     .filter(Permission.obj_type == PermissionTargetType.SCHEMA,
                             Permission.permission.in_([PermissionType.UPDATE_ENTITY,
                                                        PermissionType.READ_ENTITY]),
                             Permission.obj_id == schema_id[0])
            query = query.union(subq)

    def _prep_perm(p: Permission) -> PermissionWithIdSchema:
        perm = PermissionWithIdSchema.from_orm(p)
        return perm

    return [_prep_perm(p) for p in query.all()]


def grant_permission(data: PermissionSchema, db: Session) -> bool:
    obj_types = {
        PermissionTargetType.GROUP: Group,
        PermissionTargetType.ENTITY: Entity,
        PermissionTargetType.SCHEMA: Schema
    }

    if data.obj_id is None and data.permission in (PermissionType.CREATE_ENTITY,
                                                   PermissionType.UPDATE_ENTITY,
                                                   PermissionType.DELETE_ENTITY,
                                                   PermissionType.READ_ENTITY):
        raise ValueError("Entity-level permissions need to be tied to a specific entity or schema.")

    try:
        if data.recipient_type == RecipientType.USER:
            recipient_id = db.query(User.id).filter(User.username == data.recipient_name).one()
        elif data.recipient_type == RecipientType.GROUP:
            recipient_id = db.query(Group.id).filter(Group.name == data.recipient_name).one()
        else:
            raise ValueError("Only users and groups are allowed as recipients.")
    except sqlalchemy.exc.NoResultFound:
        if data.recipient_type == RecipientType.USER:
            raise exceptions.MissingUserException(obj_id=data.recipient_name)
        raise exceptions.MissingGroupException(obj_id=data.recipient_name)

    if (data.obj_type and not data.obj_id) or (not data.obj_type and data.obj_id):
        raise ValueError("The type and ID of the target object always need to be defined as pair.")
    args = {"permission": data.permission,
            "recipient_type": data.recipient_type,
            "recipient_id": recipient_id[0],
            }
    if data.obj_type:
        obj_type = obj_types.get(data.obj_type, None)
        if not obj_type:
            raise ValueError("Only groups, entities and schemas are allowed object types.")

        try:
            db.query(obj_type.id).filter(obj_type.id == data.obj_id).one()
        except sqlalchemy.exc.NoResultFound:
            raise exceptions.MissingObjectException(obj_id=data.obj_id,
                                                    obj_type=data.obj_type.value)
        args["obj_type"] = data.obj_type
        args["obj_id"] = data.obj_id

    try:
        permission = Permission(**args)
        db.add(permission)
        db.commit()
        return True
    except sqlalchemy.exc.IntegrityError:
        return False


def revoke_permissions(ids: List[int], db: Session) -> bool:
    count = db.query(Permission).filter(Permission.id.in_(ids)).delete()
    db.commit()
    return count > 0
