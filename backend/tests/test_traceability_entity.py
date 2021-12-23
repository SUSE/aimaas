from ..traceability import *
from ..models import *
from datetime import datetime, timedelta, timezone

import pytest


# TODO test_old_value_is_changed_after_applying_entity_update_request(dbsession: Session, client):
  

def make_entity_change_objects(db: Session, user: User, time: datetime):
    for i in range(9):
        change_request = ChangeRequest(
            created_at=time+timedelta(hours=i),
            created_by=user,
        )
        change_1 = Change(
            change_request=change_request,
            object_id=1,
            change_type=ChangeType.UPDATE,
            content_type=ContentType.ENTITY,
            field_name='name',
            data_type=ChangeAttrType.STR,
            value_id=998
        )
        change_2 = Change(
            change_request=change_request,
            object_id=1,
            change_type=ChangeType.UPDATE,
            content_type=ContentType.ENTITY,
            field_name='slug',
            data_type=ChangeAttrType.STR,
            value_id=999
        )
        db.add_all([change_request, change_1, change_2])


    change_request = ChangeRequest(
            created_at=time+timedelta(hours=9),
            created_by=user,
    )
    change_1 = Change(
        change_request=change_request,
        object_id=1,
        change_type=ChangeType.CREATE,
        content_type=ContentType.ENTITY,
        field_name='deleted',
        data_type=ChangeAttrType.STR,
        value_id=998
    )
    change_2 = Change(
        change_request=change_request,
        object_id=1,
        change_type=ChangeType.CREATE,
        content_type=ContentType.ENTITY,
        field_name='deleted',
        data_type=ChangeAttrType.STR,
        value_id=999
    )
    db.add_all([change_request, change_1, change_2])
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
    # updating age from 10 to 42
    # updating list of colors to violet and cyan
    # updating name from Jack to Jackson
    change_request = ChangeRequest(created_by=user, created_at=time)
    name_val = ChangeValueStr(old_value='Jack', new_value='Jackson')
    age_val = ChangeValueInt(old_value=10, new_value=42)
    color_val_1 = ChangeValueStr(new_value='violet')
    color_val_2 = ChangeValueStr(new_value='cyan')
    db.add_all([change_request, name_val, age_val, color_val_1, color_val_2])
    db.flush()

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

    change_kwargs = {
        'change_request': change_request, 
        'object_id': 1, 
        'content_type': ContentType.ENTITY,
        'change_type': ChangeType.UPDATE
    }
    name_change = Change(field_name='name', value_id=name_val.id, data_type=ChangeAttrType.STR, **change_kwargs)
    age_change = Change(attribute_id=age.id, value_id=age_val.id, data_type=ChangeAttrType.INT, **change_kwargs)
    color_change_1 = Change(attribute_id=fav_color.id, value_id=color_val_1.id, data_type=ChangeAttrType.STR, **change_kwargs)
    color_change_2 = Change(attribute_id=fav_color.id, value_id=color_val_2.id, data_type=ChangeAttrType.STR, **change_kwargs)
    db.add_all([name_change, age_change, color_change_1, color_change_2])
    db.commit()


def test_get_entity_update_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_entity_update_request(db=dbsession, user=user, time=now)

    change = entity_change_details(db=dbsession, change_request_id=1)
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
    assert age.new == 42 and age.old == age.current == 10
    assert fav_color.new == ['violet', 'cyan'] and fav_color.old == fav_color.current == None


def asserts_after_submitting_entity_update_request(db: Session, born_time: datetime):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.created_by is not None
    assert change_request.created_at is not None
    assert change_request.status == ChangeStatus.PENDING

    slug_change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'slug')
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.UPDATE)
        .where(Change.object_id == 1)
    ).scalar()
    slug = db.execute(select(ChangeValueStr).where(ChangeValueStr.id == slug_change.value_id)).scalar()
    assert slug.old_value == 'Jack' and slug.new_value == 'test'

    name_change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'name')
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.UPDATE)
        .where(Change.object_id == 1)
    ).scalar()
    assert name_change is None


    other_fields = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.attribute_id != None)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.UPDATE)
        .where(Change.object_id == 1)
    ).scalars().all()
    assert len(other_fields) == 4  # 1 for nickname and born, 2 for friends
    assert {'nickname', 'friends', 'born'} == {i.attribute.name for i in other_fields}
    
    values = set()
    fks = db.execute(
        select(ChangeValueForeignKey)
    ).scalars().all()
    for fk in fks:
        values.add(fk.new_value)
    values.add(db.execute(
        select(ChangeValueStr)
    ).scalars().all()[-1].new_value) # slug, nickname
    values.add(db.execute(
        select(ChangeValueDatetime)
    ).scalar().new_value)
    assert {None, 1, 2, born_time} == values

def asserts_after_applying_entity_update_request(db: Session, change_request_id: int):
    change_request = db.execute(select(ChangeRequest).where(ChangeRequest.id == change_request_id)).scalar()
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by is not None
    assert change_request.comment == 'Autosubmit'

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
        
        apply_entity_update_request(dbsession, change_request_id=1, reviewed_by=user, comment='Autosubmit')
        asserts_after_applying_entity_update_request(dbsession, change_request_id=1)

    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = ChangeRequest(created_by=user, created_at=datetime.utcnow())
        dbsession.add(schema_change)
        dbsession.flush()

        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request_id=schema_change.id, reviewed_by=user)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request_id=42, reviewed_by=user)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, user: User):
        r = ChangeRequest(created_by=user, created_at=datetime.utcnow())
        name_val = ChangeValueStr(new_value='test')
        slug_val = ChangeValueStr(new_value='test')
        schema_val = ChangeValueInt(new_value=1)
        attr_val = ChangeValueStr(new_value='test')
        dbsession.add_all([name_val, slug_val, schema_val, attr_val])
        dbsession.flush()

        name = Change(
            change_request=r, value_id=name_val.id, field_name='name', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=1
        )
        slug = Change(
            change_request=r, value_id=slug_val.id, field_name='slug', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=1
        )
        schema = Change(
            change_request=r, value_id=schema_val.id, field_name='schema_id', 
            data_type=ChangeAttrType.INT, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=1
        )
       

        a = Attribute(name='test', type=AttrType.STR)
        attr = Change(
            change_request=r, value_id=attr_val.id, attribute=a, 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=1
        )
        dbsession.add_all([r, name, slug, schema, a, attr])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_update_request(db=dbsession, change_request_id=r.id, reviewed_by=user)
      


def make_entity_delete_request(db: Session, user: User, time: datetime):
    change_request = ChangeRequest(created_by=user, created_at=time)
    del_val = ChangeValueBool(old_value=False, new_value=True)
    db.add_all([change_request, del_val])
    db.flush()
    db.add(
        Change(
            change_request=change_request,
            value_id=del_val.id,
            change_type=ChangeType.DELETE,
            content_type=ContentType.ENTITY,
            object_id=1,
            data_type=ChangeAttrType.BOOL,
            field_name='deleted'
        )
    )
    db.commit()


def test_get_entity_delete_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_entity_delete_request(db=dbsession, user=user, time=now)

    change = entity_change_details(db=dbsession, change_request_id=1)
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
    assert deleted.new == True and deleted.old == deleted.current == False


def asserts_after_submitting_entity_delete_request(db: Session):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.created_by is not None
    assert change_request.created_at is not None
    assert change_request.status == ChangeStatus.PENDING

    changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.change_type == ChangeType.DELETE)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.object_id == 1)
    ).scalars().all()
    assert len(changes) == 1
    value_id = changes[0].value_id
    value = db.execute(select(ChangeValueBool).where(ChangeValueBool.id == value_id)).scalar()
    assert value.new_value == True

def asserts_after_applying_entity_delete_request(db: Session, comment: str):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.reviewed_by is not None
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.comment == comment

class TestDeleteEntityTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_entity_delete_request_create_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.update_entity', return_value=True)
        create_entity_delete_request(dbsession, id_or_slug=1, schema_id=1, created_by=user)
        asserts_after_submitting_entity_delete_request(db=dbsession)

        apply_entity_delete_request(dbsession, change_request_id=1, reviewed_by=user, comment='test')
        asserts_after_applying_entity_delete_request(dbsession, comment='test')

    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = ChangeRequest(created_by=user, created_at=datetime.utcnow())
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request_id=schema_change.id, reviewed_by=user, comment=None)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request_id=42, reviewed_by=user, comment=None)

def asserts_after_submitting_entity_create_request(db: Session):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.created_by is not None
    assert change_request.created_at is not None
    assert change_request.status == ChangeStatus.PENDING

    born = datetime(1990, 6, 30, tzinfo=timezone.utc)
    assert db.execute(select(Entity).where(Entity.slug == 'John')).scalar() is None, 'This user should not exist'
    name_change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'name')
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalar()
    assert name_change
    name = db.execute(select(ChangeValueStr).where(ChangeValueStr.id == name_change.value_id)).scalar()
    assert name.old_value is None and name.new_value == 'John'

    slug_change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'slug')
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalar()
    assert slug_change
    slug = db.execute(select(ChangeValueStr).where(ChangeValueStr.id == slug_change.value_id)).scalar()
    assert slug.old_value is None and slug.new_value == 'John'

    schema_change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'schema_id')
        .where(Change.data_type == ChangeAttrType.INT)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalar()
    assert schema_change
    schema = db.execute(select(ChangeValueInt).where(ChangeValueInt.id == schema_change.value_id)).scalar()
    assert schema.old_value is None and schema.new_value == 1

    other_fields = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.attribute_id != None)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    assert {'nickname', 'age', 'friends', 'born'} == {i.attribute.name for i in other_fields}
    
    values = set()
    values.add(db.execute(
        select(ChangeValueInt)
    ).scalars().all()[-1].new_value) # schema_id, age
    values.add(db.execute(
        select(ChangeValueForeignKey)
    ).scalar().new_value)
    values.add(db.execute(
        select(ChangeValueStr)
    ).scalars().all()[-1].new_value) # name, slug, nickname
    values.add(db.execute(
        select(ChangeValueDatetime)
    ).scalar().new_value)
    assert {'john', 10, 1, born} == values


def asserts_after_applying_entity_create_request(db: Session, change_request_id: int):
    change_request = db.execute(select(ChangeRequest).where(ChangeRequest.id == change_request_id)).scalar()
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.reviewed_by is not None
    assert change_request.comment == 'Autosubmit'
    assert change_request.reviewed_at >= change_request.created_at


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
        
        change_request = create_entity_create_request(db=dbsession, data=p, schema_id=1, created_by=user)
        asserts_after_submitting_entity_create_request(dbsession)

        apply_entity_create_request(db=dbsession, change_request_id=change_request.id, reviewed_by=user, comment='Autosubmit')
        asserts_after_applying_entity_create_request(dbsession, change_request_id=change_request.id)
    
    def test_raise_on_missing_change(self, dbsession: Session, user: User):
        schema_change = ChangeRequest(created_by=user, created_at=datetime.utcnow())
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityCreateRequestException):
            apply_entity_create_request(db=dbsession, change_request_id=schema_change.id, reviewed_by=user)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityCreateRequestException):
            apply_entity_create_request(db=dbsession, change_request_id=42, reviewed_by=user)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, user: User):
        r = ChangeRequest(created_by=user, created_at=datetime.utcnow())
        name_val = ChangeValueStr(new_value='test')
        slug_val = ChangeValueStr(new_value='test')
        schema_val = ChangeValueInt(new_value=1)
        attr_val = ChangeValueStr(new_value='test')
        dbsession.add_all([name_val, slug_val, schema_val, attr_val])
        dbsession.flush()

        name = Change(
            change_request=r, value_id=name_val.id, field_name='name', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        slug = Change(
            change_request=r, value_id=slug_val.id, field_name='slug', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        schema = Change(
            change_request=r, value_id=schema_val.id, field_name='schema_id', 
            data_type=ChangeAttrType.INT, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
       

        a = Attribute(name='test', type=AttrType.STR)
        attr = Change(
            change_request=r, value_id=attr_val.id, attribute=a, 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        dbsession.add_all([r, name, slug, schema, a, attr])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_create_request(db=dbsession, change_request_id=r.id, reviewed_by=user)

            
def make_entity_create_request(db: Session, user: User, time: datetime):
    person = Entity(name='Jackson', slug='jackson', schema_id=1)
    db.add(person)
    db.flush()
    change_request = ChangeRequest(created_by=user, created_at=time)
    change_request.status = ChangeStatus.APPROVED
    change_request.comment = 'approved'
    name_val = ChangeValueStr(new_value='Jackson')
    slug_val = ChangeValueStr(new_value='jackson')
    age_val = ChangeValueInt(new_value=42)
    color_val_1 = ChangeValueStr(new_value='violet')
    color_val_2 = ChangeValueStr(new_value='cyan')
    db.add_all([change_request, name_val, slug_val, age_val, color_val_1, color_val_2])
    db.flush()

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

    change_kwargs = {
        'change_request': change_request, 
        'object_id': person.id, 
        'content_type': ContentType.ENTITY,
        'change_type': ChangeType.CREATE
    }
    name_change = Change(field_name='name', value_id=name_val.id, data_type=ChangeAttrType.STR, **change_kwargs)
    slug_change = Change(field_name='slug', value_id=slug_val.id, data_type=ChangeAttrType.STR, **change_kwargs)
    age_change = Change(attribute_id=age.id, value_id=age_val.id, data_type=ChangeAttrType.INT, **change_kwargs)
    color_change_1 = Change(attribute_id=fav_color.id, value_id=color_val_1.id, data_type=ChangeAttrType.STR, **change_kwargs)
    color_change_2 = Change(attribute_id=fav_color.id, value_id=color_val_2.id, data_type=ChangeAttrType.STR, **change_kwargs)
    db.add_all([name_change, slug_change, age_change, color_change_1, color_change_2])
    db.commit()


def test_get_entity_create_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_entity_create_request(db=dbsession, user=user, time=now)

    change = entity_change_details(db=dbsession, change_request_id=1)
    assert change.created_at == now
    assert change.created_by == user.username
    assert change.reviewed_at is None
    assert change.reviewed_by is None
    assert change.comment == 'approved'
    assert change.status == ChangeStatus.APPROVED
    assert change.entity.name == 'Jackson'
    assert change.entity.slug == 'jackson'
    assert change.entity.schema_slug == 'person'
    assert len(change.changes) == 4
    name = change.changes['name']
    age = change.changes['age']
    slug = change.changes['slug']
    fav_color = change.changes['fav_color']
    assert name.new == 'Jackson' and name.old is None
    assert age.new == 42 and age.old is None
    assert slug.new == 'jackson' and slug.old is None
    assert fav_color.new == ['violet', 'cyan'] and fav_color.old == fav_color.current == None