from datetime import datetime

from ..models import *
from ..schemas import *
from ..exceptions import *
from ..crud import *
from .entity import *
from .schema import *


def decline_change_request(db: Session, change_request_id: int, change_object: ChangeObject, change_type: ChangeType, reviewed_by: User, comment: Optional[str]) -> ChangeRequest:
    change_request = db.execute(select(ChangeRequest).where(ChangeRequest.id == change_request_id)).scalar()
    if change_request is None:
        raise MissingChangeException(obj_id=change_request_id)
    change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request_id)
        .where(Change.change_type == change_type)
        .where(Change.content_type == ContentType[change_object.name])
    ).scalar()
    if not change:
        raise MissingChangeException(obj_id=change_request_id)

    change_request.status = ChangeStatus.DECLINED
    change_request.comment = comment
    change_request.reviewed_at = datetime.utcnow()
    change_request.reviewed_by = reviewed_by
    db.commit()
    return change_request


def review_changes(db: Session, change_request_id: int, review: ChangeReviewSchema, reviewed_by=User):
    if review.result == ReviewResult.DECLINE:
        return decline_change_request(
            db=db, 
            change_request_id=change_request_id, 
            change_object=review.change_object, 
            change_type=review.change_type, 
            reviewed_by=reviewed_by,
            comment=review.comment
        )
    kwargs = {'db': db, 'change_request_id': change_request_id, 'reviewed_by': reviewed_by, 'comment': review.comment}
    if review.change_object == ChangeObject.SCHEMA:
        if review.change_type == ChangeType.CREATE:
            return apply_schema_create_request(**kwargs)
        elif review.change_type == ChangeType.UPDATE:
            return apply_schema_update_request(**kwargs)
        elif review.change_type == ChangeType.DELETE:
            return apply_schema_delete_request(**kwargs)

    elif review.change_object == ChangeObject.ENTITY:
        if review.change_type == ChangeType.CREATE:
            return apply_entity_create_request(**kwargs)
        elif review.change_type == ChangeType.UPDATE:
            return apply_entity_update_request(**kwargs)
        elif review.change_type == ChangeType.DELETE:
            return apply_entity_delete_request(**kwargs)


def get_pending_change_requests(db: Session, obj_type: Optional[ContentType] = None, limit: Optional[int] = 10, offset: Optional[int] = 0, all: Optional[bool] = False) -> List[ChangeRequest]:
    q = select(ChangeRequest).where(ChangeRequest.status == ChangeStatus.PENDING)
    if obj_type is not None:
        q = q.join(Change).where(Change.content_type == obj_type).distinct()
    if not all:
        q = q.offset(offset).limit(limit)
    q = q.order_by(ChangeRequest.created_at.desc())
    return db.execute(q).scalars().all()