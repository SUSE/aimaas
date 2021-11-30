from datetime import datetime

from ..models import *
from ..schemas import *
from ..exceptions import *
from ..crud import *
from .entity import *
from .schema import *


def decline_change_request(db: Session, change_id: int, change_object: ChangeObject, change_type: ChangeType, reviewed_by: User, comment: Optional[str]) -> Change:
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == change_object)
        .where(Change.change_type == change_type)
    ).scalar()
    if change is None:
        raise Exception('NO CHANGE NO CHANGE')
    change.status = ChangeStatus.DECLINED
    change.comment = comment
    change.reviewed_at = datetime.utcnow()
    change.reviewed_by = reviewed_by
    db.commit()
    return change


def review_changes(db: Session, change_id: int, review: ChangeReviewSchema, reviewed_by=User):
    if review.result == ReviewResult.DECLINE:
        return decline_change_request(
            db=db, 
            change_id=change_id, 
            change_object=review.change_object, 
            change_type=review.change_type, 
            reviewed_by=reviewed_by,
            comment=review.comment
        )
    if review.change_object == ChangeObject.SCHEMA:
        pass
    elif review.change_object == ChangeObject.ENTITY:
        if review.change_type == ChangeType.CREATE:
            pass
        elif review.change_type == ChangeType.UPDATE:
            return apply_entity_update_request(db=db, change_id=change_id, reviewed_by=reviewed_by, comment=review.comment)
