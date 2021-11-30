import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# from backend.auth import get_password_hash

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
    
    ### Users

    id | username | password 
    ---|----------|---------
     1 |  admin   | admin       
       |          |                  


    ### Permissions
    
    id | obj_id | obj_type |       name      |
    ---|--------|----------|-----------------|
     1 |  null  |  SCHEMA  |     CREATE      |
     2 |  null  |  SCHEMA  |     UPDATE      |
     3 |  null  |  SCHEMA  |     DELETE      |
     4 |  null  |  ENTITY  |     CREATE      |
     5 |  null  |  ENTITY  |     UPDATE      |
     6 |  null  |  ENTITY  |     DELETE      |
     7 |  1000  |  SCHEMA  |     CREATE      |
       |        |          |                 |   

    ### User permissions
    
    id | user      | perm_id  |
    ---|-----------|----------|
     1 |  admin[1] |     1    |
       |           |          |  

    ### Groups
    
    id |  name     | parent group
    ---|-----------|-------------
     1 | GroupA    |  None
     2 | GroupBA   |  GroupA
     3 | GroupCA   |  GroupA
     4 | GroupDB   |  GroupBA
     5 | GroupEC   |  GroupCA
       |           |  

    ### Group permissions
    
    id | group      | perm_id  |
    ---|------------|----------|
     1 | GroupA[1]  |     7    |
       |            |          |
   
    
    ### Groups users
    
    id | group       | user       |
    ---|-------------|------------|
     1 | GroupEC[5]  |  admin[1]  |
       |             |            | 
    '''    
    # from .. import auth
    admin = User(username='admin', email='admin@example.com', password='12345')# password=auth.get_password_hash('admin'))
    # perm_c_sch = Permission(obj_id=None, obj_type=PermObject.SCHEMA, name=PermType.CREATE)
    # perms = [Permission(obj_id=None, obj_type=PermObject.SCHEMA, name=PermType.UPDATE),
    #     Permission(obj_id=None, obj_type=PermObject.SCHEMA, name=PermType.DELETE),
    #     Permission(obj_id=None, obj_type=PermObject.ENTITY, name=PermType.CREATE),
    #     Permission(obj_id=None, obj_type=PermObject.ENTITY, name=PermType.UPDATE),
    #     Permission(obj_id=None, obj_type=PermObject.ENTITY, name=PermType.DELETE),]
    db.add(admin)
    # db.add_all(perms)
    # db.add_all([
    #     UserPermission(user=admin, permission=perm_c_sch),
    #     Permission(obj_id=1000, obj_type=PermObject.SCHEMA, name=PermType.CREATE)
    # ])
    # for perm in perms:
    #     db.add(UserPermission(user=admin, permission=perm))

    # groupA = Group(name='groupA')
    # groupBA = Group(name='groupBA', parent=groupA)
    # groupCA = Group(name='groupCA', parent=groupA)
    # groupDB = Group(name='groupDB', parent=groupBA)
    # groupEC = Group(name='groupEC', parent=groupCA)

    # db.add_all([
    #     groupA, 
    #     groupBA, 
    #     groupCA, 
    #     groupDB, 
    #     groupEC,
    #     UserGroup(user=admin, group=groupEC),
    #     GroupPermission(group=groupA, permission_id=7)
    # ])
    
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
    bfk = BoundFK(attr_def_id=friends_.id, schema_id=person.id)
    db.add(bfk)

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
    # from .. import auth
    # from ..auth import Depends, oauth2_scheme
    # db = TestingSessionLocal()
    # user = db.execute(select(User)).scalar()
    # db.close()
    # async def override_get_user(
    #     db: Session = Depends(database.get_db), 
    #         token: str = Depends(oauth2_scheme)
    #     ):
    #     return user
    # def override_authorize(*args, **kwargs):
    #     return True

    # auth.get_current_user = override_get_user
    # auth.is_authorized = override_authorize
    from .. import create_app
    app = create_app()
    # app.dependency_overrides[auth.get_current_user] = override_get_user
    

    client = TestClient(app)
    # put = client.put
    # def put_override(*args, **kwargs):
    #     kwargs['headers'] = {'Authorization': 'Bearer qwe'}
    #     return put(*args, **kwargs)
    # client.put = put_override
    return client
    
@pytest.fixture
def client(engine):
    yield client_(engine)

