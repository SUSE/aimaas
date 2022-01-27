from datetime import timedelta, timezone, datetime
from itertools import groupby

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.models import User
from ..models import Schema, Attribute, AttrType, AttributeDefinition
from ..schemas.schema import AttrDefSchema, SchemaCreateSchema, AttrDefUpdateSchema, \
    SchemaUpdateSchema
from ..traceability.enum import ChangeType, ContentType, EditableObjectType, ChangeStatus
from ..traceability.models import ChangeRequest, Change, ChangeAttrType, ChangeValueStr, \
    ChangeValueBool, ChangeValueInt
from ..traceability.schema import get_recent_schema_changes, schema_change_details, \
    create_schema_create_request, apply_schema_create_request, get_value_for_change, \
    create_schema_update_request, apply_schema_update_request, create_schema_delete_request, \
    apply_schema_delete_request

from .test_traceability_entity import make_entity_change_objects

def make_schema_change_objects(db: Session, user: User, time: datetime):
    requests = []
    for i in range(9):
        change_request = ChangeRequest(
            created_at=time+timedelta(hours=i),
            created_by=user,
            object_type=EditableObjectType.SCHEMA,
            object_id=1,
            change_type=ChangeType.UPDATE
        )
        change_1 = Change(
            change_request=change_request,
            object_id=1,
            change_type=ChangeType.UPDATE,
            content_type=ContentType.SCHEMA,
            field_name='name',
            data_type=ChangeAttrType.STR,
            value_id=998
        )
        change_2 = Change(
            change_request=change_request,
            object_id=1,
            change_type=ChangeType.UPDATE,
            content_type=ContentType.SCHEMA,
            field_name='slug',
            data_type=ChangeAttrType.STR,
            value_id=999
        )
        db.add_all([change_request, change_1, change_2])
        requests.append(change_request)


    change_request = ChangeRequest(
            created_at=time+timedelta(hours=9),
            created_by=user,
            object_type=EditableObjectType.SCHEMA,
            object_id=1,
            change_type=ChangeType.CREATE
    )
    change_1 = Change(
        change_request=change_request,
        object_id=1,
        change_type=ChangeType.CREATE,
        content_type=ContentType.SCHEMA,
        field_name='deleted',
        data_type=ChangeAttrType.STR,
        value_id=998
    )
    change_2 = Change(
        change_request=change_request,
        object_id=1,
        change_type=ChangeType.CREATE,
        content_type=ContentType.SCHEMA,
        field_name='deleted',
        data_type=ChangeAttrType.STR,
        value_id=999
    )
    db.add_all([change_request, change_1, change_2])
    requests.append(change_request)
    db.commit()
    return requests


def test_get_recent_schema_changes(dbsession: Session):
    time = datetime.now(timezone.utc)
    user = dbsession.execute(select(User)).scalar()
    make_schema_change_objects(db=dbsession, user=user, time=time)
    entities = make_entity_change_objects(db=dbsession, user=user, time=time)
    changes, entity_requests = get_recent_schema_changes(db=dbsession, schema_id=1, count=1)
    assert changes[0].created_at.astimezone(timezone.utc) == (time + timedelta(hours=9))
    assert len(entity_requests) == 1 and entity_requests[0] == entities[-1]

    changes, entity_requests = get_recent_schema_changes(db=dbsession, schema_id=1, count=5)
    for change, i in zip(changes, reversed(range(5, 10))):
        assert change.created_at.astimezone(timezone.utc) == (time + timedelta(hours=i))
    assert len(entity_requests) == 1 and entity_requests[0] == entities[-1]


def make_schema_create_request(db: Session, user: User, time: datetime):
    schema = Schema(name='Test', slug='test', reviewable=True)
    db.add(schema)
    db.flush()
    change_request = ChangeRequest(
        created_by=user, 
        created_at=time, 
        status=ChangeStatus.APPROVED,
        object_type=EditableObjectType.SCHEMA,
        object_id=schema.id,
        change_type=ChangeType.CREATE
    )
    slug_val = ChangeValueStr(new_value='test')
    reviewable_val = ChangeValueBool(new_value=True)

    db.add_all([slug_val, reviewable_val])
    db.flush()
    schema_data = {
        'slug': {'old': None, 'new': 'test'}, 
        'reviewable': {'old': None, 'new': True},
        'name': {'old': None, 'new': 'Test'}
    }
    schema_fields = [('name', ChangeAttrType.STR), ('slug', ChangeAttrType.STR), ('reviewable', ChangeAttrType.BOOL)]
    for field, type_ in schema_fields:
        ValueModel = type_.value.model
        v = ValueModel(new_value=schema_data[field]['new'], old_value=schema_data[field]['old']) 
        db.add(v)
        db.flush()
        db.add(Change(
            change_request=change_request,
            field_name=field,
            value_id=v.id,
            object_id=schema.id,
            data_type=type_,
            content_type=ContentType.SCHEMA,
            change_type=ChangeType.CREATE
        ))
    
    v = ChangeValueInt(new_value=schema.id)
    db.add(v)
    db.flush()
    db.add(Change(
        change_request=change_request,
        field_name='id',
        value_id=v.id,
        object_id=schema.id,
        data_type=ChangeAttrType.INT,
        content_type=ContentType.SCHEMA,
        change_type=ChangeType.UPDATE
    ))

    attr_fields = [
        ('required', ChangeAttrType.BOOL, False), 
        ('unique', ChangeAttrType.BOOL, False), 
        ('list', ChangeAttrType.BOOL, False), 
        ('key', ChangeAttrType.BOOL, False),
        ('description', ChangeAttrType.STR, None),
        ('bind_to_schema', ChangeAttrType.INT, None),
        ('name', ChangeAttrType.STR, 'test'),
        ('type', ChangeAttrType.STR, 'STR'),
    ]
    test = Attribute(name='test', type=AttrType.STR)
    db.add(test)
    db.flush()
    for attr, data_type, value in attr_fields:
        ValueModel = data_type.value.model
        v = ValueModel(new_value=value)
        db.add(v)
        db.flush()
        change = Change(
                change_request=change_request,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE,
                field_name=attr,
                object_id=test.id,
                value_id=v.id,
                data_type=data_type,
            )
        
        db.add(change)
    db.commit()


def test_get_schema_create_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_schema_create_request(db=dbsession, user=user, time=now)

    change = schema_change_details(db=dbsession, change_request_id=1)
    assert change.created_at == now
    assert change.created_by == user.username
    assert change.reviewed_at is None
    assert change.reviewed_by is None
    assert change.comment is None
    assert change.status == ChangeStatus.APPROVED
    assert change.schema_.name == 'Test' and  change.schema_.slug == 'test'
    changes = change.changes
    assert changes.slug['new'] == 'test' and changes.slug['old'] == None
    assert changes.reviewable['new'] == True and changes.reviewable['old'] == None
    assert changes.name['new'] == 'Test' and changes.name['old'] == None
    add = changes.add
    assert len(add) == 1
    assert add[0] == AttrDefSchema(
        name='test',
        type='STR',
        required=False,
        unique=False,
        list=False,
        key=False,
    )


def asserts_after_submitting_schema_create_request(db: Session):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.created_by is not None
    assert change_request.created_at is not None
    assert change_request.status == ChangeStatus.PENDING
    def get_value_for_change(change):
        ValueModel = change.data_type.value.model
        return db.execute(select(ValueModel).where(ValueModel.id == change.value_id)).scalar()


    s = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()

    schema_attrs = {
        ('name', 'Car'),
        ('slug', 'car'),
        ('reviewable', False)
    }
    assert len(s) == len(schema_attrs)
    s_attrs = {(i.field_name, get_value_for_change(i).new_value) for i in s}
    assert schema_attrs == s_attrs

    a = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()

    data = TestCreateSchemaTraceability.data_for_test(db)
    assert len(a) == len(data['attr_defs']) * 8  # AttributeDefinition has 8 fields
    from itertools import groupby

    for attr_id, changes in groupby(a, key=lambda x: x.object_id):
        attr = db.execute(select(Attribute).where(Attribute.id == attr_id)).scalar()
        testdata_attr = data['attr_defs'][attr.name]
        testdata_attr = {k: v for k, v in testdata_attr.dict().items()}
        testdata_attr['type'] = testdata_attr['type'].name
        change_attr = {i.field_name: get_value_for_change(i).new_value for i in changes}
        assert change_attr == testdata_attr


def asserts_after_applying_schema_create_request(db: Session, change_request_id: int, comment: str):
    change_request = db.execute(select(ChangeRequest).where(ChangeRequest.id == change_request_id)).scalar()
    assert change_request.comment == comment 
    assert change_request.reviewed_by is not None
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.reviewed_at >= change_request.created_at

class TestCreateSchemaTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()
    
    @staticmethod
    def data_for_test(db: Session) -> dict:
        color_ = AttrDefSchema(
            name='color',
            type='STR',
            required=False,
            unique=False,
            list=False,
            key=False,
            description='Color of this car'
        )
        max_speed_ = AttrDefSchema(
            name='max_speed',
            type='INT',
            required=True,
            unique=False,
            list=False,
            key=False
        )
        release_year_ = AttrDefSchema(
            name="release_year",
            type='DT',
            required=False,
            unique=False,
            list=False,
            key=False
        )
        owner_ = AttrDefSchema(
            name='owner',
            type='FK',
            required=True,
            unique=False,
            list=False,
            key=False,
            bind_to_schema=1
        )
        return {
            'attr_defs': {
                'color': color_,
                'max_speed': max_speed_,
                'release_year': release_year_,
                'owner': owner_
            }
        }

    def test_schema_create_request_and_apply(self, dbsession: Session, user: User):
        data = self.data_for_test(dbsession)
        car = SchemaCreateSchema(name='Car', slug='car', attributes=list(data['attr_defs'].values()))

        cr = create_schema_create_request(db=dbsession, data=car, created_by=user)
        asserts_after_submitting_schema_create_request(db=dbsession)
        
        apply_schema_create_request(db=dbsession, change_request=cr, reviewed_by=user, comment='test')
        asserts_after_applying_schema_create_request(db=dbsession, change_request_id=1, comment='test')


def make_schema_update_request(db: Session, user: User, time: datetime):
    change_request = ChangeRequest(
        created_by=user, 
        created_at=time,
        object_type=EditableObjectType.SCHEMA,
        object_id=1,
        change_type=ChangeType.UPDATE
    )
    slug_val = ChangeValueStr(old_value='person', new_value='test')
    reviewable_val = ChangeValueBool(old_value=False, new_value=True)
    db.add_all([slug_val, reviewable_val])
    db.flush()
    ########## SCHEMA UPD #######
    schema_data = {
        'slug': {'old': 'person', 'new': 'test'}, 
        'reviewable': {'old': False, 'new': True},
        'name': {'old': 'Person', 'new': None}
    }
    schema_fields = [('name', ChangeAttrType.STR), ('slug', ChangeAttrType.STR), ('reviewable', ChangeAttrType.BOOL)]
    for field, type_ in schema_fields:
        ValueModel = type_.value.model
        v = ValueModel(new_value=schema_data[field]['new'], old_value=schema_data[field]['old']) 
        db.add(v)
        db.flush()
        db.add(Change(
            change_request=change_request,
            field_name=field,
            value_id=v.id,
            object_id=1,
            data_type=type_,
            content_type=ContentType.SCHEMA,
            change_type=ChangeType.UPDATE
        ))
    
    v = ChangeValueInt(new_value=1)
    db.add(v)
    db.flush()
    db.add(Change(
        change_request=change_request,
        field_name='id',
        value_id=v.id,
        object_id=1,
        data_type=ChangeAttrType.INT,
        content_type=ContentType.SCHEMA,
        change_type=ChangeType.UPDATE
    ))

    ########## ATTR UPD #########
    attr_fields = [
        ('required', (ChangeAttrType.BOOL, True, True)), 
        ('unique', (ChangeAttrType.BOOL, False, True)), 
        ('list',(ChangeAttrType.BOOL, False, True)), 
        ('key', (ChangeAttrType.BOOL, True, True)),
        ('description', (ChangeAttrType.STR, 'Age of this person', 'AGE')),
        ('bind_to_schema', (ChangeAttrType.INT, None, None)),
        ('name', (ChangeAttrType.STR, 'age', 'AGE')),
        ('new_name', (ChangeAttrType.STR, 'age', 'AGE')),
        # ('type', ChangeAttrType.STR)
    ]
    age = db.execute(select(Attribute).where(Attribute.name == 'age').where(Attribute.type == AttrType.INT)).scalar()

    change_kwargs = {
        'change_request': change_request,
        'content_type': ContentType.ATTRIBUTE_DEFINITION,
        'change_type': ChangeType.UPDATE
    }
    for attr, (data_type, old, new) in attr_fields:
        ValueModel = data_type.value.model
        v = ValueModel(old_value=old, new_value=new)
        db.add(v)
        db.flush()
        db.add(
            Change(
                field_name=attr,
                object_id=age.id,
                value_id=v.id,
                data_type=data_type,
                **change_kwargs
            )
        )
    ########## ATTR ADD #########
    attr_fields = [
        ('required', ChangeAttrType.BOOL, False), 
        ('unique', ChangeAttrType.BOOL, False), 
        ('list', ChangeAttrType.BOOL, False), 
        ('key', ChangeAttrType.BOOL, False),
        ('description', ChangeAttrType.STR, None),
        ('bind_to_schema', ChangeAttrType.INT, None),
        ('name', ChangeAttrType.STR, 'test'),
        ('type', ChangeAttrType.STR, 'STR'),
    ]
    test = Attribute(name='test', type=AttrType.STR)
    db.add(test)
    db.flush()
    for attr, data_type, value in attr_fields:
        ValueModel = data_type.value.model
        v = ValueModel(new_value=value)
        db.add(v)
        db.flush()
        change = Change(
                change_request=change_request,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE,
                field_name=attr,
                object_id=test.id,
                value_id=v.id,
                data_type=data_type,
            )
        
        db.add(change)
    ########## ATTR DEL #########
    born = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == 1)
        .join(Attribute)
        .where(Attribute.name == 'born')
    ).scalar().attribute
    v = ChangeValueStr(new_value='born')
    db.add(v)                                # but models require value_id
    db.flush()
    db.add(Change(
        change_request=change_request,
        attribute_id=born.id,
        value_id=v.id,
        data_type=ChangeAttrType.STR,
        content_type=ContentType.ATTRIBUTE_DEFINITION,
        change_type=ChangeType.DELETE
    ))
    db.commit()


def test_get_schema_update_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_schema_update_request(db=dbsession, user=user, time=now)

    change = schema_change_details(db=dbsession, change_request_id=1)
    assert change.created_at == now
    assert change.created_by == user.username
    assert change.reviewed_at is None
    assert change.reviewed_by is None
    assert change.comment is None
    assert change.status == ChangeStatus.PENDING
    assert change.schema_.name == 'Person' and  change.schema_.slug == 'person'
    changes = change.changes
    assert changes.slug['new'] == 'test' and changes.slug['old'] == changes.slug['current'] == 'person'
    assert changes.reviewable['new'] == True and changes.reviewable['old'] == changes.reviewable['current'] == False
    assert changes.name is None
    add = changes.add
    upd = changes.update
    delete = changes.delete
    assert all(len(i) == 1 for i in [add, upd, delete])
    assert add[0] == AttrDefSchema(
        name='test',
        type='STR',
        required=False,
        unique=False,
        list=False,
        key=False,
    )
    assert upd[0] == AttrDefUpdateSchema(
        name='age',
        new_name='AGE',
        required=True,
        unique=True,
        list=True,
        key=True,
        description='AGE'
    )
    assert delete[0] == 'born'


def asserts_after_submitting_schema_update_request(db: Session, data: SchemaUpdateSchema):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.created_by is not None
    assert change_request.created_at is not None
    assert change_request.status == ChangeStatus.PENDING

    schema_changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalars().all()
    assert len(schema_changes) == 4                                  # this one wasnt passed but let it be
    passed_data = {'name': None, 'slug': 'test', 'reviewable': True, 'id': 1}
    change_data = {i.field_name: get_value_for_change(i, db).new_value for i in schema_changes}
    assert passed_data == change_data
    assert schema_changes[0].object_id == 1


    attr_upd = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalars().all()
    attr_upd = {k: [i for i in v] for k, v in groupby(attr_upd, key=lambda x: x.object_id)}
    assert len(attr_upd.keys()) == 1, 'Only one attr was updated'

    attr_fields = [
        'new_name', 'required', 'list', 
        'key', 'unique', 'description', 
        'name', 'bind_to_schema'
    ]
    for attr_id, changes in attr_upd.items():
        attr_data = {field: getattr(data.update_attributes[0], field) for field in attr_fields}
        change_data = {i.field_name: get_value_for_change(i, db).new_value for i in changes}
        assert attr_data == change_data

    attr_create = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    attr_create = {k: [i for i in v] for k, v in groupby(attr_create, key=lambda x: x.object_id)}
    assert len(attr_create.keys()) == 1, 'Only one attr was created'
    
    attr_fields = [
        'type', 'required', 'list', 
        'key', 'unique', 'description', 
        'name', 'bind_to_schema'
    ]
    for attr_id, changes in attr_create.items():
        attr_data = {field: getattr(data.add_attributes[0], field) for field in attr_fields}
        attr_data['type'] = attr_data['type'].name
        change_data = {i.field_name: get_value_for_change(i, db).new_value for i in changes}
        assert attr_data == change_data

    attr_delete = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.attribute_id != None)
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalars().all()
    assert len(attr_delete) == 1
    assert attr_delete[0].attribute.name == 'born'
    
def asserts_after_applying_schema_update_request(db: Session, comment: str):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by is not None
    assert change_request.comment == comment
    assert change_request.status == ChangeStatus.APPROVED

class TestUpdateSchemaTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_schema_update_request_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.update_schema', return_value=True)
        
        data = SchemaUpdateSchema(
            slug='test',
            reviewable=True,
            update_attributes=[
                AttrDefUpdateSchema(
                    name='age',
                    required=False,
                    unique=False,
                    list=False,
                    key=False,
                    description='Age of this person'
                )
            ], 
            add_attributes=[
                AttrDefSchema(
                    name='address',
                    type='FK',
                    required=True,
                    unique=True,
                    list=True,
                    key=True,
                    bind_to_schema=-1
                )
            ],
            delete_attributes=['born']
        )
        cr = create_schema_update_request(dbsession, 1, data, user)
        asserts_after_submitting_schema_update_request(db=dbsession, data=data)

        apply_schema_update_request(db=dbsession, change_request=cr, reviewed_by=user, comment='test')
        asserts_after_applying_schema_update_request(db=dbsession, comment='test')


def asserts_after_submitting_schema_delete_request(db: Session):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.status == ChangeStatus.PENDING
    assert change_request.created_at is not None
    assert change_request.created_by is not None

    changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'deleted')
        .where(Change.object_id == 1)
        .where(Change.data_type == ChangeAttrType.BOOL)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalars().all()
    assert len(changes) == 1
    v = get_value_for_change(changes[0], db)
    assert v.new_value

def asserts_after_applying_schema_delete_request(db: Session, comment: str):
    change_request = db.execute(select(ChangeRequest)).scalar()
    assert change_request.reviewed_at >= change_request.created_at
    assert change_request.reviewed_by is not None
    assert change_request.status == ChangeStatus.APPROVED
    assert change_request.comment == comment

class TestDeleteSchemaTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_delete_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.delete_schema', return_value=True)

        cr = create_schema_delete_request(db=dbsession, id_or_slug=1, created_by=user)
        asserts_after_submitting_schema_delete_request(db=dbsession)

        apply_schema_delete_request(db=dbsession, change_request=cr, reviewed_by=user, comment='test')
        asserts_after_applying_schema_delete_request(db=dbsession, comment='test')


# TODO schema delete details