import pytest

from ..traceability import *
from ..models import *


@pytest.mark.parametrize(['content_type', 'change_type'], [
    (ContentType.ENTITY, ChangeType.CREATE),
    (ContentType.ENTITY, ChangeType.UPDATE),
    (ContentType.ENTITY, ChangeType.DELETE),
    (ContentType.SCHEMA, ChangeType.CREATE),
    (ContentType.SCHEMA, ChangeType.UPDATE),
    (ContentType.SCHEMA, ChangeType.DELETE),
])
def test_decline_change_request(dbsession: Session, content_type, change_type):
    user = dbsession.execute(select(User)).scalar()
    change_request = ChangeRequest(created_at=datetime.utcnow(), created_by=user)
    v = ChangeValueStr()
    dbsession.add_all([change_request, v])
    dbsession.flush()
    change = Change(
        change_request=change_request,
        value_id=v.id,
        change_type=change_type,
        content_type=content_type,
        field_name='test',
        data_type=ChangeAttrType.STR
    )
    dbsession.add(change)
    dbsession.commit()

    decline_change_request(
        db=dbsession, 
        change_request_id=change_request.id,
        change_object=ChangeObject[content_type.name],
        change_type=change_type,
        reviewed_by=user,
        comment='test'
    )

    assert change_request.status == ChangeStatus.DECLINED
    assert change_request.comment == 'test'
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by == user


def make_change_for_review(db: Session) -> ChangeRequest:
    user = db.execute(select(User)).scalar()
    change_request = ChangeRequest(created_at=datetime.utcnow(), created_by=user)
    v = ChangeValueStr(new_value='test')
    db.add_all([change_request, v])
    db.flush()
    change = Change(
        change_request=change_request,
        value_id=v.id,
        change_type=ChangeType.UPDATE,
        object_id=1,
        content_type=ContentType.ENTITY,
        field_name='name',
        data_type=ChangeAttrType.STR
    )
    db.add(change)
    db.commit()
    return change_request


def test_review_changes(dbsession: Session):
    user = dbsession.execute(select(User)).scalar()
    change_request = make_change_for_review(db=dbsession)
    
    review = ChangeReviewSchema(
        result=ReviewResult.APPROVE,
        change_object=ChangeObject.ENTITY,
        change_type=ChangeType.UPDATE,
        comment='test'
    )
    # approve
    review_changes(
        db=dbsession, 
        change_request_id=change_request.id,
        review=review,
        reviewed_by=user
    )
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.comment == 'test'
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by == user

    change_request.status = ChangeStatus.PENDING
    dbsession.flush()
    # decline
    review.result = ReviewResult.DECLINE
    review.comment = 'test2'
    review_changes(
        db=dbsession, 
        change_request_id=change_request.id,
        review=review,
        reviewed_by=user
    )

    assert change_request.status == ChangeStatus.DECLINED
    assert change_request.comment == 'test2'
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by == user