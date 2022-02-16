from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from ..auth import authenticated_user, authorized_user
from ..auth.crud import get_or_create_user, get_user, grant_permission
from ..auth.enum import RecipientType, PermissionType
from ..auth.models import User
from ..database import get_db
from ..models import *
from ..config import settings as s
from ..schemas.auth import UserCreateSchema, PermissionSchema
from ..traceability.enum import EditableObjectType, ChangeType, ContentType
from ..traceability.models import ChangeRequest, Change, ChangeAttrType, ChangeValueInt
from .. import create_app


TEST_USER = UserCreateSchema(
    username="tester",
    password="password",
    email="tester@tests.org",
    firstname="Test",
    lastname="Test"
)


def fake_authenticated_user(db: Session, username_override: Optional[str] = None):
    async def _auth_user():
        return get_user(db=db, username=username_override or TEST_USER.username)

    return _auth_user


def populate_db(db: Session):
    '''Populates DB with following data:
    
    ### Attributes

        name   | id | type
        -------|----|-----
        age    |  1 | FLOAT
        age    |  2 | INT
        age    |  3 | STR
        born   |  4 | DT
        friends|  5 | FK
        address|  6 | FK
      nickname |  7 | STR
      fav_color|  8 | STR

    ### Schemas
      1. Person (person), fields:

      name   | attr_id | required | unique | list | key
      -------|---------|----------|--------|------|----
      age    |    2    |     +    |   -    |   -  |  + 
      born   |    4    |     -    |   -    |   -  |  - 
      friends|    5    |     +    |   -    |   +  |  - 
    nickname |    7    |     -    |   +    |   -  |  -
    fav_color|    8    |     -    |   -    |   +  |  -

    ### Bound FKs

    schema | attribute | bound to
    -------|-----------|---------
    Person |  friends  | Person

    ### Entities
      *Person*

      id |  slug  | age | born | friends | nickname | name | fav_color
      ---|--------|-----|------|---------|----------|------|----------
      1  | Jack   | 10  |   -  |   []    | jack     | Jack | red, blue
      2  | Jane   | 12  |   -  |   [1]   | jane     | Jane | red, black
    
    '''
    user, _ = get_or_create_user(db=db, data=TEST_USER)
    grant_permission(data=PermissionSchema(
        recipient_type=RecipientType.USER,
        recipient_name=user.username,
        permission=PermissionType.SUPERUSER
    ), db=db)

    age_float = Attribute(name='age', type=AttrType.FLOAT)
    age_int = Attribute(name='age', type=AttrType.INT)
    age_str = Attribute(name='age', type=AttrType.STR)
    born = Attribute(name='born', type=AttrType.DT)
    friends = Attribute(name='friends', type=AttrType.FK)
    address = Attribute(name='address', type=AttrType.FK)
    nickname = Attribute(name='nickname', type=AttrType.STR)
    fav_color = Attribute(name='fav_color', type=AttrType.STR)
    db.add_all([age_float, age_int, age_str, born, friends, address, nickname, fav_color])

    person = Schema(name='Person', slug='person')
    db.add(person)
    db.flush()
    
    age_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=age_int.id,
        required=True,
        unique=False,
        list=False,
        key=True,
        description='Age of this person'
    )
    born_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=born.id,
        required=False,
        unique=False,
        list=False,
        key=False
    )
    friends_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=friends.id,
        required=True,
        unique=False,
        list=True,
        key=False,
        bound_schema_id=person.id
    )
    nickname_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=nickname.id,
        required=False,
        unique=True,
        list=False,
        key=False
    )
    fav_color_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=fav_color.id,
        required=False,
        unique=False,
        list=True,
        key=False
    )
    db.add_all([age_, born_, friends_, nickname_, fav_color_])
    db.flush()

    p1 = Entity(schema_id=person.id, slug='Jack', name='Jack')
    db.add(p1)
    db.flush()
    p1_nickname = ValueStr(entity_id=p1.id, attribute_id=nickname.id, value='jack')
    p1_age = ValueInt(entity_id=p1.id, attribute_id=age_int.id, value=10)
    p1_fav_color_1 = ValueStr(value='red', entity_id=p1.id, attribute_id=fav_color.id)
    p1_fav_color_2 = ValueStr(value='blue', entity_id=p1.id, attribute_id=fav_color.id)

    p2 = Entity(schema_id=person.id, slug='Jane', name='Jane')
    db.add(p2)
    db.flush()
    p2_nickname = ValueStr(entity_id=p2.id, attribute_id=nickname.id, value='jane')
    p2_age = ValueInt(entity_id=p2.id, attribute_id=age_int.id, value=12)
    p2_friend = ValueForeignKey(entity_id=p2.id, attribute_id=friends.id, value=p1.id)
    p2_fav_color_1 = ValueStr(value='red', entity_id=p2.id, attribute_id=fav_color.id)
    p2_fav_color_2 = ValueStr(value='black', entity_id=p2.id, attribute_id=fav_color.id)

    db.add_all([p1_nickname, p1_age, p2_nickname, p2_age, p2_friend,p1_fav_color_1, p1_fav_color_2, p2_fav_color_1, p2_fav_color_2])

    unperson = Schema(name="UnPerson", slug="unperson")
    db.add(unperson)

    time = datetime.now(timezone.utc)

    # Some change requests for entities
    for i in range(-12, -3):
        change_request = ChangeRequest(
            created_at=time+timedelta(hours=i),
            created_by=user,
            object_type=EditableObjectType.ENTITY,
            object_id=1,
            change_type=ChangeType.UPDATE
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
            created_at=time+timedelta(hours=-9),
            created_by=user,
            object_type=EditableObjectType.ENTITY,
            object_id=1,
            change_type=ChangeType.CREATE
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
    schema_value = ChangeValueInt(new_value=1)
    db.add(schema_value)
    db.flush()
    change_3 = Change(
        change_request=change_request,
        object_id=1,
        change_type=ChangeType.CREATE,
        content_type=ContentType.ENTITY,
        field_name='schema_id',
        data_type=ChangeAttrType.INT,
        value_id=schema_value.id
    )
    db.add_all([change_request, change_1, change_2, change_3])

    # And some change requests for schemas
    for i in range(-12, -3):
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

    change_request = ChangeRequest(
        created_at=time+timedelta(hours=9),
        created_by=user,
        object_type=EditableObjectType.SCHEMA,
        object_id=1,
        change_type=ChangeType.CREATE,
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
    db.commit()


@pytest.fixture(scope="session")
def engine():
    url = f"postgresql+psycopg2://{s.test_pg_user}:{s.test_pg_password}@{s.test_pg_host}:{s.test_pg_port}/{s.test_pg_db}"
    return create_engine(url)


@pytest.fixture
def tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    populate_db(session)
    session.close()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def dbsession(engine, tables) -> Session:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def testuser(dbsession) -> User:
    return get_user(db=dbsession, username=TEST_USER.username)


@pytest.fixture
def client(dbsession):
    app = create_app(session=dbsession)
    app.dependency_overrides[get_db] = lambda: dbsession
    client = TestClient(app)
    yield client


@pytest.fixture
def authenticated_client(client, dbsession):
    client.app.dependency_overrides[authenticated_user] = fake_authenticated_user(db=dbsession)
    yield client


@pytest.fixture
def authorized_client(authenticated_client, dbsession):
    client = authenticated_client
    client.app.dependency_overrides[authorized_user] = fake_authenticated_user(db=dbsession)
    yield client
