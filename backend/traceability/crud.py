import typing
from datetime import datetime, timezone
from typing import Optional, List

from fastapi.exceptions import HTTPException
from fastapi_pagination import Params, Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select, desc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_403_FORBIDDEN

from ..exceptions import MissingChangeException, MissingChangeRequestException
from ..auth.crud import has_permission
from ..auth.enum import PermissionType
from ..auth.models import User
from ..models import Schema, Entity
from ..schemas.auth import RequirePermission
from ..schemas.traceability import ChangeReviewSchema

from .enum import EditableObjectType, ChangeType, ChangeStatus, ReviewResult, ContentType
from .models import ChangeRequest, Change, ChangeValueInt
from .entity import apply_entity_create_request, apply_entity_update_request, \
    apply_entity_delete_request
from .schema import apply_schema_create_request, apply_schema_update_request, \
    apply_schema_delete_request


REQUIRED_PERMISSIONS = {
    (EditableObjectType.SCHEMA, ChangeType.CREATE): (PermissionType.CREATE_SCHEMA, Schema),
    (EditableObjectType.SCHEMA, ChangeType.UPDATE): (PermissionType.UPDATE_SCHEMA, Schema),
    (EditableObjectType.SCHEMA, ChangeType.DELETE): (PermissionType.DELETE_SCHEMA, Schema),
    (EditableObjectType.ENTITY, ChangeType.CREATE): (PermissionType.CREATE_ENTITY, Schema),
    (EditableObjectType.ENTITY, ChangeType.UPDATE): (PermissionType.UPDATE_ENTITY, Entity),
    (EditableObjectType.ENTITY, ChangeType.DELETE): (PermissionType.DELETE_ENTITY, Entity),
}


def is_user_authorized_to_review(db: Session, user: User, request_id: int) -> None:
    request = get_change_request(db=db, request_id=request_id)
    req_perm, Model = REQUIRED_PERMISSIONS.get((request.object_type, request.change_type))
    req_perm = RequirePermission(permission=req_perm)
    if request.object_type == EditableObjectType.ENTITY \
            and request.change_type == ChangeType.CREATE:
        try:
            schema_id = db\
                .query(ChangeValueInt.new_value)\
                .join(Change, ChangeValueInt.id == Change.value_id)\
                .filter(Change.change_request_id == request.id, Change.field_name == "schema_id")\
                .scalar()
        except NoResultFound:
            schema_id = None
        req_perm.target = Model(id=schema_id)
    else:
        req_perm.target = Model(id=request.object_id)

    if not has_permission(db=db, user=user, permission=req_perm):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN,
                            detail="You are not authorized for this action")


def get_change_request(db: Session, request_id: int) -> ChangeRequest:
    try:
        return db.query(ChangeRequest).filter(ChangeRequest.id == request_id).one()
    except NoResultFound:
        raise MissingChangeRequestException(obj_id=request_id)


def decline_change_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                           comment: Optional[str]) -> ChangeRequest:
    change_request.status = ChangeStatus.DECLINED
    change_request.comment = comment
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.reviewed_by = reviewed_by
    db.commit()
    return change_request


def review_changes(db: Session, change_request_id: int, review: ChangeReviewSchema,
                   reviewed_by: User) -> typing.Tuple[ChangeRequest, bool]:
    try:
        change_request = db.query(ChangeRequest).filter(ChangeRequest.id == change_request_id).one()
    except NoResultFound:
        raise MissingChangeRequestException(obj_id=change_request_id)
    if change_request.status != ChangeStatus.PENDING:
        return change_request, False

    if review.result == ReviewResult.DECLINE:
        decline_change_request(
            db=db,
            change_request=change_request,
            reviewed_by=reviewed_by,
            comment=review.comment
        )
        return change_request, True
    kwargs = {'db': db, 'change_request': change_request, 'reviewed_by': reviewed_by,
              'comment': review.comment}

    changed = False
    if change_request.object_type == EditableObjectType.SCHEMA:
        if change_request.change_type == ChangeType.CREATE:
            changed |= apply_schema_create_request(**kwargs)[0]
        elif change_request.change_type == ChangeType.UPDATE:
            changed |= apply_schema_update_request(**kwargs)[0]
        elif change_request.change_type == ChangeType.DELETE:
            changed |= apply_schema_delete_request(**kwargs)[0]

    elif change_request.object_type == EditableObjectType.ENTITY:
        if change_request.change_type == ChangeType.CREATE:
            changed |= apply_entity_create_request(**kwargs)[0]
        elif change_request.change_type == ChangeType.UPDATE:
            changed |= apply_entity_update_request(**kwargs)[0]
        elif change_request.change_type == ChangeType.DELETE:
            changed |= apply_entity_delete_request(**kwargs)[0]

    return change_request, changed


def get_pending_change_requests(params: Params, db: Session,
                                obj_type: Optional[EditableObjectType] = None) -> Page[ChangeRequest]:
    q = db.query(ChangeRequest) \
        .filter(ChangeRequest.status == ChangeStatus.PENDING) \
        .order_by(ChangeRequest.created_at.desc())

    if obj_type:
        q = q.filter(ChangeRequest.object_type == obj_type)

    return paginate(q, params)
