from datetime import datetime
from typing import Optional, List

from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.status import HTTP_403_FORBIDDEN

from ..exceptions import MissingChangeException, MissingChangeRequestException
from ..auth.crud import has_permission
from ..auth.enum import PermissionType
from ..auth.models import User
from ..schemas.auth import RequirePermission
from ..schemas.traceability import ChangeReviewSchema

from .enum import EditableObjectType, ChangeType, ChangeStatus, ReviewResult, ContentType
from .models import ChangeRequest, Change
from .entity import apply_entity_create_request, apply_entity_update_request, apply_entity_delete_request
from .schema import apply_schema_create_request, apply_schema_update_request, apply_schema_delete_request


def is_user_authorized_to_review(db: Session, user: User, request_id: int) -> None:
    request = get_change_request(db=db, request_id=request_id)
    hp = False
    if request.object_type == EditableObjectType.ENTITY:
        hp = has_permission(db=db, user=user,
                            permission=RequirePermission(permission=PermissionType.UPDATE_ENTITY))
    elif request.object_type == EditableObjectType.SCHEMA:
        hp = has_permission(db=db, user=user,
                            permission=RequirePermission(permission=PermissionType.UPDATE_SCHEMA))
    if not hp:
        raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="You are not authorized for this action"
            )


def get_change_request(db: Session, request_id: int) -> ChangeRequest:
    try:
        return db.query(ChangeRequest).filter(ChangeRequest.id == request_id).one()
    except NoResultFound:
        raise MissingChangeRequestException(obj_id=request_id)


def decline_change_request(db: Session, change_request_id: int, change_object: EditableObjectType,
                           change_type: ChangeType, reviewed_by: User, comment: Optional[str]) -> ChangeRequest:
    change_request = db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.id == change_request_id)
        .where(ChangeRequest.change_type == change_type)
        .where(ChangeRequest.object_type == change_object)
    ).scalar()
    if change_request is None:
        raise MissingChangeException(obj_id=change_request_id)

    change_request.status = ChangeStatus.DECLINED
    change_request.comment = comment
    change_request.reviewed_at = datetime.utcnow()
    change_request.reviewed_by = reviewed_by
    db.commit()
    return change_request


def review_changes(db: Session, change_request_id: int, review: ChangeReviewSchema, reviewed_by=User):
    change_request = db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.id == change_request_id)
        .where(ChangeRequest.status == ChangeStatus.PENDING)
    ).scalar()
    if change_request is None:
        raise MissingChangeException(obj_id=change_request_id)

    if review.result == ReviewResult.DECLINE:
        return decline_change_request(
            db=db,
            change_request_id=change_request_id,
            change_object=change_request.object_type,
            change_type=change_request.change_type,
            reviewed_by=reviewed_by,
            comment=review.comment
        )
    kwargs = {'db': db, 'change_request_id': change_request_id, 'reviewed_by': reviewed_by, 'comment': review.comment}
    if change_request.object_type == EditableObjectType.SCHEMA:
        if change_request.change_type == ChangeType.CREATE:
            return apply_schema_create_request(**kwargs)
        elif change_request.change_type == ChangeType.UPDATE:
            return apply_schema_update_request(**kwargs)
        elif change_request.change_type == ChangeType.DELETE:
            return apply_schema_delete_request(**kwargs)

    elif change_request.object_type == EditableObjectType.ENTITY:
        if change_request.change_type == ChangeType.CREATE:
            return apply_entity_create_request(**kwargs)
        elif change_request.change_type == ChangeType.UPDATE:
            return apply_entity_update_request(**kwargs)
        elif change_request.change_type == ChangeType.DELETE:
            return apply_entity_delete_request(**kwargs)


def get_pending_change_requests(db: Session, obj_type: Optional[ContentType] = None,
                                limit: Optional[int] = 10, offset: Optional[int] = 0,
                                all: Optional[bool] = False) -> List[ChangeRequest]:
    q = select(ChangeRequest).where(ChangeRequest.status == ChangeStatus.PENDING)
    if obj_type is not None:
        q = q.join(Change).where(Change.content_type == obj_type).distinct()
    if not all:
        q = q.offset(offset).limit(limit)
    q = q.order_by(ChangeRequest.created_at.desc())
    return db.execute(q).scalars().all()
