import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from ..models import *
from ..config import settings as s

from ..main import app, get_db

def populate_db(db: Session):
    '''Populates DB with following data:
    
    ### Attributes

        name   | id | type
        -------|----|-----
        name   |  1 | STR
        age    |  2 | FLOAT
        age    |  3 | INT
        age    |  4 | STR
        born   |  5 | DT
        friends|  6 | FK
        address|  7 | FK

    ### Schemas
      1. Person (person), fields:

      name   | attr_id | required | unique | list | key
      -------|---------|----------|--------|------|----
      name   |    1    |     +    |   +    |   -  |  + 
      age    |    3    |     +    |   -    |   -  |  + 
      born   |    5    |     -    |   -    |   -  |  - 
      friends|    6    |     +    |   -    |   +  |  - 

    ### Bound FKs

    schema | attribute | bound to
    -------|-----------|---------
    Person |  friends  | Person

    ### Entities
      *Person*

      id |  name  | age | born | friends
      ---|--------|-----|------|--------
      1  | Jack   | 10  |   -  |   []
      2  | Jane   | 12  |   -  |   [1]
    
    '''
    name = Attribute(name='name', type=AttrType.STR)
    age_float = Attribute(name='age', type=AttrType.FLOAT)
    age_int = Attribute(name='age', type=AttrType.INT)
    age_str = Attribute(name='age', type=AttrType.STR)
    born = Attribute(name='born', type=AttrType.DT)
    friends = Attribute(name='friends', type=AttrType.FK)
    address = Attribute(name='address', type=AttrType.FK)
    db.add_all([name, age_float, age_int, age_str, born, friends, address])

    person = Schema(name='Person', slug='person')
    db.add(person)
    db.flush()

    name_ = AttributeDefinition(
        schema_id=person.id,
        attribute_id=name.id,
        required=True,
        unique=True,
        list=False,
        key=True,
        description='Name of this person'
    )
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
    db.add_all([name_, age_, born_, friends_])
    db.flush()
    bfk = BoundFK(attr_def_id=friends_.id, schema_id=person.id)
    db.add(bfk)

    p1 = Entity(schema_id=person.id)
    db.add(p1)
    db.flush()
    p1_name = ValueStr(entity_id=p1.id, attribute_id=name.id, value='Jack')
    p1_age = ValueInt(entity_id=p1.id, attribute_id=age_int.id, value=10)

    p2 = Entity(schema_id=person.id)
    db.add(p2)
    db.flush()
    p2_name = ValueStr(entity_id=p2.id, attribute_id=name.id, value='Jane')
    p2_age = ValueInt(entity_id=p2.id, attribute_id=age_int.id, value=12)
    p2_friend = ValueForeignKey(entity_id=p2.id, attribute_id=friends.id, value=p1.id)

    db.add_all([p1_name, p1_age, p2_name, p2_age, p2_friend])
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


@pytest.fixture
def client(engine):
    def override_get_db():
        try:
            TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
        
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client