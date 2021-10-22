import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from ..models import *
from ..config import settings as s
from .. import database


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

    ### Schemas
      1. Person (person), fields:

      name   | attr_id | required | unique | list | key
      -------|---------|----------|--------|------|----
      age    |    2    |     +    |   -    |   -  |  + 
      born   |    4    |     -    |   -    |   -  |  - 
      friends|    5    |     +    |   -    |   +  |  - 
    nickname |    7    |     -    |   +    |   -  |  -

    ### Bound FKs

    schema | attribute | bound to
    -------|-----------|---------
    Person |  friends  | Person

    ### Entities
      *Person*

      id |  slug  | age | born | friends | nickname | name
      ---|--------|-----|------|---------|----------|-----
      1  | Jack   | 10  |   -  |   []    | jack     | Jack
      2  | Jane   | 12  |   -  |   [1]   | jane     | Jane
    
    '''
    age_float = Attribute(name='age', type=AttrType.FLOAT)
    age_int = Attribute(name='age', type=AttrType.INT)
    age_str = Attribute(name='age', type=AttrType.STR)
    born = Attribute(name='born', type=AttrType.DT)
    friends = Attribute(name='friends', type=AttrType.FK)
    address = Attribute(name='address', type=AttrType.FK)
    nickname = Attribute(name='nickname', type=AttrType.STR)
    db.add_all([age_float, age_int, age_str, born, friends, address, nickname])

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
        key=False
    )
    nickname_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=nickname.id,
        required=False,
        unique=True,
        list=False,
        key=False
    )
    db.add_all([age_, born_, friends_, nickname_])
    db.flush()
    bfk = BoundFK(attr_def_id=friends_.id, schema_id=person.id)
    db.add(bfk)

    p1 = Entity(schema_id=person.id, slug='Jack', name='Jack')
    db.add(p1)
    db.flush()
    p1_nickname = ValueStr(entity_id=p1.id, attribute_id=nickname.id, value='jack')
    p1_age = ValueInt(entity_id=p1.id, attribute_id=age_int.id, value=10)

    p2 = Entity(schema_id=person.id, slug='Jane', name='Jane')
    db.add(p2)
    db.flush()
    p2_nickname = ValueStr(entity_id=p2.id, attribute_id=nickname.id, value='jane')
    p2_age = ValueInt(entity_id=p2.id, attribute_id=age_int.id, value=12)
    p2_friend = ValueForeignKey(entity_id=p2.id, attribute_id=friends.id, value=p1.id)

    db.add_all([p1_nickname, p1_age, p2_nickname, p2_age, p2_friend])
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
def dbsession(engine, tables):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def client_(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
            
    database.get_db = override_get_db
    database.SessionLocal = TestingSessionLocal
    from .. import create_app
    app = create_app()

    client = TestClient(app)
    return client
    
@pytest.fixture
def client(engine):
    yield client_(engine)

