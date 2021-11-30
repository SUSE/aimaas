from ..traceability import *
from ..models import *
from datetime import datetime, timedelta, timezone

import pytest


# TODO test_old_value_is_changed_after_applying_entity_update_request(dbsession: Session, client):
  

def make_entity_change_objects(db: Session, user: User, time: datetime):
    for i in range(9):
        change = Change(
                created_at=time+timedelta(hours=i),
                created_by=user,
                change_object=ChangeObject.ENTITY,
                change_type=ChangeType.UPDATE
        )
        ent_upd = EntityUpdate(change=change, entity_id=1)
        db.add_all([change, ent_upd])
    change = Change(
        created_at=time+timedelta(hours=9),
        created_by=user,
        change_object=ChangeObject.ENTITY,
        change_type=ChangeType.DELETE
    )
    ent_upd = EntityUpdate(change=change, entity_id=1)
    db.add_all([change, ent_upd])
    db.commit()

def test_get_recent_entity_changes(dbsession: Session):
    time = datetime.utcnow()
    user = dbsession.execute(select(User)).scalar()
    make_entity_change_objects(db=dbsession, user=user, time=time)

    changes = get_recent_entity_changes(db=dbsession, entity_id=1, count=1)
    assert changes[0].created_at == (time + timedelta(hours=9)).replace(tzinfo=timezone.utc)

    changes = get_recent_entity_changes(db=dbsession, entity_id=1, count=5)
    for change, i in zip(changes, reversed(range(5, 10))):
        assert change.created_at == (time + timedelta(hours=i)).replace(tzinfo=timezone.utc)


def make_entity_update_request(db: Session, user: User, time: datetime):
    change = Change(created_by=user, created_at=time, change_object=ChangeObject.ENTITY, change_type=ChangeType.UPDATE)
    entity = db.execute(select(Entity)).scalar()
    ent_upd = EntityUpdate(change=change, entity=entity, new_name='Jackson', old_name='Jack')
    age = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == 1)
        .join(Attribute)
        .where(Attribute.name == 'age')
    ).scalar().attribute

    fav_color = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == 1)
        .join(Attribute)
        .where(Attribute.name == 'fav_color')
    ).scalar().attribute
    age_upd = ValueUpdate(change=change, entity=entity, attribute=age, old_value='10', new_value='42')
    fav_color_upd_1 = ValueUpdate(change=change, entity=entity, attribute=fav_color, new_value='violet')
    fav_color_upd_2 = ValueUpdate(change=change, entity=entity, attribute=fav_color, new_value='cyan')
    db.add_all([change, ent_upd, age_upd, fav_color_upd_1, fav_color_upd_2])
    db.commit()


def test_get_entity_update_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_entity_update_request(db=dbsession, user=user, time=now)

    change = entity_change_details(db=dbsession, change_id=1)
    assert change.created_at == now
    assert change.created_by == user.username
    assert change.reviewed_at is None
    assert change.reviewed_by is None
    assert change.comment is None
    assert change.status == ChangeStatus.PENDING
    assert change.entity.name == 'Jack'
    assert change.entity.slug == 'Jack'
    assert change.entity.schema_slug == 'person'
    assert len(change.changes) == 3
    name = change.changes['name']
    age = change.changes['age']
    fav_color = change.changes['fav_color']
    assert name.new == 'Jackson' and name.old == name.current == 'Jack'
    assert age.new == '42' and age.old == age.current == '10'
    assert fav_color.new == ['violet', 'cyan'] and fav_color.old == fav_color.current == None


def asserts_after_submitting_entity_update_request(db: Session, born_time: datetime):
    change = db.execute(select(Change)).scalar()
    assert change.created_by is not None
    assert change.created_at is not None
    assert change.change_object == ChangeObject.ENTITY
    assert change.change_type == ChangeType.UPDATE
    assert change.status == ChangeStatus.PENDING

    ent_upd = db.execute(select(EntityUpdate).where(EntityUpdate.change_id == change.id)).scalar()
    assert ent_upd is not None
    assert ent_upd.new_name == None and ent_upd.new_slug == 'test'
    val_upd = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == 1)).scalars().all()

    assert {'friends', 'nickname', 'born'} == {i.attribute.name for i in val_upd}
    assert {None, '1', '2', str(born_time)} == {i.new_value for i in val_upd}

def asserts_after_applying_entity_update_request(db: Session, change_id: int):
    change = db.execute(select(Change).where(Change.id == change_id)).scalar()
    assert change.status == ChangeStatus.APPROVED
    assert change.reviewed_at is not None
    assert change.reviewed_by == change.created_by
    assert change.comment == 'Autosubmit'


class TestUpdateEntityTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_entity_update_request_change_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.update_entity', return_value=True)
        time = datetime.now(timezone.utc)
        data = {
            'slug': 'test',
            'nickname': None,
            'born': time,
            'friends': [1, 2],
        }
        create_entity_update_request(dbsession, 1, 1, data, user)
        asserts_after_submitting_entity_update_request(dbsession, born_time=time)
        
        apply_entity_update_request(dbsession, change_id=1, reviewed_by=user, comment='Autosubmit')
        asserts_after_applying_entity_update_request(dbsession, change_id=1)

    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = Change(created_by=user, created_at=datetime.utcnow(), change_object=ChangeObject.SCHEMA, change_type=ChangeType.CREATE)
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_id=schema_change.id, reviewed_by=user)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_id=42, reviewed_by=user)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, user: User):
        e = dbsession.execute(select(Entity)).scalar()
        c = Change(
            created_by=user, created_at=datetime.utcnow(), 
            change_object=ChangeObject.ENTITY, 
            change_type=ChangeType.UPDATE
        )
        a = Attribute(name='test', type=AttrType.STR)
        ent_upd = EntityUpdate(change=c, entity=e)
        v = ValueUpdate(change=c, attribute=a, entity=e, old_value=None, new_value='test')
        dbsession.add_all([c, ent_upd, a, v])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_update_request(db=dbsession, change_id=c.id, reviewed_by=user)


def make_entity_delete_request(db: Session, user: User, time: datetime):
    change = Change(created_by=user, created_at=time, change_object=ChangeObject.ENTITY, change_type=ChangeType.UPDATE)
    entity = db.execute(select(Entity)).scalar()
    ent_upd = EntityUpdate(change=change, entity=entity, new_deleted=True, old_deleted=False)
    db.add_all([change, ent_upd])
    db.commit()


def test_get_entity_delete_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_entity_delete_request(db=dbsession, user=user, time=now)

    change = entity_change_details(db=dbsession, change_id=1)
    assert change.created_at == now
    assert change.created_by == user.username
    assert change.reviewed_at is None
    assert change.reviewed_by is None
    assert change.comment is None
    assert change.status == ChangeStatus.PENDING
    assert change.entity.name == 'Jack'
    assert change.entity.slug == 'Jack'
    assert change.entity.schema_slug == 'person'
    assert len(change.changes) == 1
    deleted = change.changes['deleted']
    assert deleted.new == 'True' and deleted.old == deleted.current == 'False'


def asserts_after_submitting_entity_delete_request(db: Session):
    change = db.execute(select(Change)).scalar()
    assert change.created_by is not None
    assert change.created_at is not None
    assert change.change_object == ChangeObject.ENTITY
    assert change.change_type == ChangeType.DELETE
    assert change.status == ChangeStatus.PENDING

    ent_upd = db.execute(select(EntityUpdate).where(EntityUpdate.change_id == change.id)).scalar()
    assert ent_upd is not None
    assert ent_upd.new_deleted == True and ent_upd.old_deleted == False
    assert ent_upd.new_name is None and ent_upd.new_slug is None
    val_upd = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change.id)).scalar()
    assert val_upd is None

def asserts_after_applying_entity_delete_request(db: Session, comment: str):
    change = db.execute(select(Change)).scalar()
    assert change.reviewed_by is not None
    assert change.reviewed_at >= change.created_at
    assert change.status == ChangeStatus.APPROVED
    assert change.comment == comment

    val_upd = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change.id)).scalar()
    assert val_upd is None


class TestDeleteEntityTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_entity_delete_request_create_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.update_entity', return_value=True)
        create_entity_delete_request(dbsession, id_or_slug=1, schema_id=1, created_by=user)
        asserts_after_submitting_entity_delete_request(db=dbsession)

        apply_entity_delete_request(dbsession, change_id=1, reviewed_by=user, comment='test')
        asserts_after_applying_entity_delete_request(dbsession, comment='test')

    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = Change(created_by=user, created_at=datetime.utcnow(), change_object=ChangeObject.SCHEMA, change_type=ChangeType.CREATE)
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_id=schema_change.id, reviewed_by=user, comment=None)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_id=42, reviewed_by=user, comment=None)


def asserts_after_submitting_entity_create_request(db: Session):
    change = db.execute(select(Change)).scalar()
    assert change.created_by is not None
    assert change.created_at is not None
    assert change.change_object == ChangeObject.ENTITY
    assert change.change_type == ChangeType.CREATE
    assert change.status == ChangeStatus.PENDING

    born = datetime(1990, 6, 30, tzinfo=timezone.utc)
    assert db.execute(select(Entity).where(Entity.slug == 'John')).scalar() is None, 'This user should not exist'
    # Check that all traceability records are present
    ent_create = db.execute(select(EntityCreate).where(EntityCreate.change_id == 1)).scalar()
    assert ent_create.name == 'John' and ent_create.slug == 'John'
    
    val_create = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == 1)).scalars().all()
    assert {'nickname', 'age', 'friends', 'born'} == {i.attribute.name for i in val_create}
    assert {'john', '10', '1', str(born)} == {i.new_value for i in val_create}
    for v in val_create:
        assert v.entity_id == None

def asserts_after_applying_entity_create_request(db: Session, change_id: int):
    persons = db.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
    person = persons[-1]
    val_create = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change_id)).scalars().all()
    for v in val_create:
        assert v.entity_id == person.id

    change = db.execute(select(Change).where(Change.id == change_id)).scalar()
    ent_create = db.execute(select(EntityCreate).where(EntityCreate.change_id == change_id)).scalar()
    assert ent_create is not None
    assert change.status == ChangeStatus.APPROVED
    assert change.reviewed_by == change.created_by
    assert change.comment == 'Autosubmit'
    assert change.reviewed_at is not None


class TestCreateEntityTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_entity_create_request_and_approve(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.create_entity', return_value=True)

        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        p = {
                'name': 'John',
                'slug': 'John',
                'nickname': 'john',
                'age': 10,
                'friends': [1],
                'born': born
            }
        user = dbsession.execute(select(User).where(User.id == 1)).scalar()
        
        change = create_entity_create_request(db=dbsession, data=p, schema_id=1, created_by=user)
        asserts_after_submitting_entity_create_request(dbsession)

        apply_entity_create_request(db=dbsession, change_id=change.id, reviewed_by=user, comment='Autosubmit')
        asserts_after_applying_entity_create_request(dbsession, change_id=1)
    
    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = Change(created_by=user, created_at=datetime.utcnow(), change_object=ChangeObject.SCHEMA, change_type=ChangeType.CREATE)
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityCreateRequestException):
            apply_entity_create_request(db=dbsession, change_id=schema_change.id, reviewed_by=user)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityCreateRequestException):
            apply_entity_create_request(db=dbsession, change_id=42, reviewed_by=user)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, user: User):
        c = Change(
            created_by=user, created_at=datetime.utcnow(), 
            change_object=ChangeObject.ENTITY, 
            change_type=ChangeType.CREATE
        )
        a = Attribute(name='test', type=AttrType.STR)
        ent_create = EntityCreate(change=c, name='test', slug='test', schema_id=1)
        v = ValueUpdate(change=c, attribute=a, old_value=None, new_value='test')
        dbsession.add_all([c, ent_create, a, v])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_create_request(db=dbsession, change_id=c.id, reviewed_by=user)


            
