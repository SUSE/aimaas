from datetime import timedelta, timezone

import pytest

from ..traceability import *
from ..models import *


def make_schema_change_objects(db: Session, user: User, time: datetime):
    for i in range(9):
        change = Change(
                created_at=time+timedelta(hours=i),
                created_by=user,
                change_object=ChangeObject.SCHEMA,
                change_type=ChangeType.UPDATE
        )
        sch_upd = SchemaUpdate(change=change, schema_id=1)
        db.add_all([change, sch_upd])
    change = Change(
        created_at=time+timedelta(hours=9),
        created_by=user,
        change_object=ChangeObject.SCHEMA,
        change_type=ChangeType.DELETE
    )
    sch_upd = SchemaUpdate(change=change, schema_id=1)
    db.add_all([change, sch_upd])
    db.commit()

def test_get_recent_schema_changes(dbsession: Session):
    time = datetime.utcnow()
    user = dbsession.execute(select(User)).scalar()
    make_schema_change_objects(db=dbsession, user=user, time=time)

    changes = get_recent_schema_changes(db=dbsession, schema_id=1, count=1)
    assert changes[0].created_at == (time + timedelta(hours=9)).replace(tzinfo=timezone.utc)

    changes = get_recent_schema_changes(db=dbsession, schema_id=1, count=5)
    for change, i in zip(changes, reversed(range(5, 10))):
        assert change.created_at == (time + timedelta(hours=i)).replace(tzinfo=timezone.utc)


def asserts_after_submitting_schema_create_request(db: Session):
    change = db.execute(select(Change)).scalar()
    assert change.created_by is not None
    assert change.created_at is not None
    assert change.change_object == ChangeObject.SCHEMA
    assert change.change_type == ChangeType.CREATE
    assert change.status == ChangeStatus.PENDING

    schema_create = db.execute(select(SchemaCreate).where(SchemaCreate.change_id == change.id)).scalar()
    assert schema_create is not None
    assert schema_create.name == 'Car' and schema_create.slug == 'car' and schema_create.reviewable == False
    
    create_attrs = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    data = TestCreateSchemaTraceability.data_for_test(db)
    for i in create_attrs:
        attr = data['attr_defs'][i.name]
        assert i.name == attr.name and i.type.name == attr.type.name
        fields = ['required', 'list', 'key', 'required', 'description', 'bind_to_schema']
        for field in fields:
            assert getattr(i, field) == getattr(attr, field)

def asserts_after_applying_schema_create_request(db: Session, change_id: int, comment: str):
    change = db.execute(select(Change).where(Change.id == change_id)).scalar()
    assert change.comment == comment 
    assert change.reviewed_by == change.created_by
    assert change.status == ChangeStatus.APPROVED
    assert change.reviewed_at >= change.created_at

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

    def test_schema_create_request_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.create_schema', return_value=True)

        data = self.data_for_test(dbsession)
        car = SchemaCreateSchema(name='Car', slug='car', attributes=list(data['attr_defs'].values()))

        create_schema_create_request(db=dbsession, data=car, created_by=user)
        asserts_after_submitting_schema_create_request(db=dbsession)
        
        apply_schema_create_request(db=dbsession, change_id=1, reviewed_by=user, comment='test')
        asserts_after_applying_schema_create_request(db=dbsession, change_id=1, comment='test')


def make_schema_update_request(db: Session, user: User, time: datetime):
    change = Change(created_by=user, created_at=time, change_object=ChangeObject.SCHEMA, change_type=ChangeType.UPDATE)
    schema = db.execute(select(Schema)).scalar()
    sch_upd = SchemaUpdate(change=change, schema=schema, new_slug='test', old_slug='person', new_reviewable=True, old_reviewable=False)
    
    attr_create = AttributeCreate(
        change=change,
        name='test',
        type='STR',
        required=False,
        unique=False,
        list=False,
        key=False
    )
    attr_update = AttributeUpdate(
        change=change,
        attribute=db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'age')
        ).scalar().attribute,
        new_name='AGE',
        required=True,
        unique=True,
        list=True,
        key=True,
        description='AGE'
    )
    attr_delete = AttributeDelete(
        change=change,
        attribute=db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == 1)
            .join(Attribute)
            .where(Attribute.name == 'born')
        ).scalar().attribute,
    )
    
    db.add_all([change, sch_upd, attr_create, attr_update, attr_delete])
    db.commit()


def test_get_schema_update_details(dbsession: Session):
    user = dbsession.execute(select(User).where(User.id == 1)).scalar()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    make_schema_update_request(db=dbsession, user=user, time=now)

    change = schema_change_details(db=dbsession, change_id=1)
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
    change = db.execute(select(Change)).scalar()
    assert change.created_by is not None
    assert change.created_at is not None
    assert change.change_object == ChangeObject.SCHEMA
    assert change.change_type == ChangeType.UPDATE
    assert change.status == ChangeStatus.PENDING
    
    schema_update = db.execute(select(SchemaUpdate).where(SchemaUpdate.change_id == change.id)).scalar()
    assert schema_update.new_name == None and schema_update.new_slug == 'test'
    assert schema_update.new_reviewable == data.reviewable

    attr_upd = db.execute(select(AttributeUpdate).where(AttributeUpdate.change_id == change.id)).scalars().all()
    assert len(attr_upd) == 1
    attr_upd = attr_upd[0]
    assert attr_upd.new_name == data.update_attributes[0].new_name
    assert attr_upd.required == data.update_attributes[0].required
    assert attr_upd.list == data.update_attributes[0].list
    assert attr_upd.key == data.update_attributes[0].key
    assert attr_upd.unique == data.update_attributes[0].unique
    assert attr_upd.description == data.update_attributes[0].description

    attr_create = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    assert len(attr_create) == 1
    attr_create = attr_create[0]
    assert attr_create.required == data.add_attributes[0].required
    assert attr_create.list == data.add_attributes[0].list
    assert attr_create.key == data.add_attributes[0].key
    assert attr_create.unique == data.add_attributes[0].unique
    assert attr_create.description == data.add_attributes[0].description
    assert attr_create.bind_to_schema == 1  # changed from -1 to actual schema id

    attr_delete = db.execute(select(AttributeDelete).where(AttributeDelete.change_id == 1)).scalars().all()
    assert len(attr_delete) == 1
    assert attr_delete[0].attribute.name == 'born'

def asserts_after_applying_schema_update_request(db: Session, comment: str):
    change = db.execute(select(Change).where(Change.id == 1)).scalar()
    assert change.reviewed_at >= change.created_at
    assert change.reviewed_by is not None
    assert change.comment == comment
    assert change.status == ChangeStatus.APPROVED

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
        create_schema_update_request(dbsession, 1, data, user)
        asserts_after_submitting_schema_update_request(db=dbsession, data=data)

        apply_schema_update_request(db=dbsession, change_id=1, reviewed_by=user, comment='test')
        asserts_after_applying_schema_update_request(db=dbsession, comment='test')


def asserts_after_submitting_schema_delete_request(db: Session):
    change: Change = db.execute(select(Change)).scalar()
    assert change.change_object == ChangeObject.SCHEMA
    assert change.change_type == ChangeType.DELETE
    assert change.status == ChangeStatus.PENDING
    assert change.created_at is not None
    assert change.created_by is not None

    sch_upd = db.execute(select(SchemaUpdate).where(SchemaUpdate.change_id == change.id)).scalar()
    assert sch_upd.schema_id == 1
    assert sch_upd.new_deleted

    attr_create = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    attr_upd = db.execute(select(AttributeUpdate).where(AttributeUpdate.change_id == change.id)).scalars().all()
    attr_delete = db.execute(select(AttributeDelete).where(AttributeDelete.change_id == change.id)).scalars().all() 
    assert not any([attr_create, attr_upd, attr_delete])

def asserts_after_applying_schema_delete_request(db: Session, comment: str):
    change: Change = db.execute(select(Change)).scalar()
    assert change.reviewed_at >= change.created_at
    assert change.reviewed_by is not None
    assert change.status == ChangeStatus.APPROVED
    assert change.comment == comment

    attr_create = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    attr_upd = db.execute(select(AttributeUpdate).where(AttributeUpdate.change_id == change.id)).scalars().all()
    attr_delete = db.execute(select(AttributeDelete).where(AttributeDelete.change_id == change.id)).scalars().all() 
    assert not any([attr_create, attr_upd, attr_delete])

class TestDeleteSchemaTraceability:
    @pytest.fixture
    def user(self, dbsession):
        return dbsession.execute(select(User).where(User.id == 1)).scalar()

    def test_delete_and_apply(self, mocker, dbsession: Session, user: User):
        mocker.patch('backend.crud.delete_schema', return_value=True)

        create_schema_delete_request(db=dbsession, id_or_slug=1, created_by=user)
        asserts_after_submitting_schema_delete_request(db=dbsession)

        apply_schema_delete_request(db=dbsession, change_id=1, reviewed_by=user, comment='test')
        asserts_after_applying_schema_delete_request(db=dbsession, comment='test')
