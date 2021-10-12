from datetime import datetime

import pytest

from ..config import *
from ..crud import *
from ..models import *
from ..schemas import *
from ..exceptions import *


class TestEntityCreate:
    def test_create(self, dbsession):
        born = datetime(1990, 6, 30)
        p1 = {
            'name': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        p1 = create_entity(dbsession, schema_id=1, data=p1)
        p2 = {
            'name': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [p1.id, 1],
            'born': born.timestamp()
        }
        p2 = create_entity(dbsession, schema_id=1, data=p2)

        persons = dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
        assert len(persons) == 4
        assert persons[-1].name == 'John'
        assert persons[-1].get('nickname', dbsession).value == 'john'
        assert persons[-1].get('age', dbsession).value == 10
        assert persons[-1].get('born', dbsession).value == born
        assert isinstance(persons[-1].get('age', dbsession), ValueInt)
        assert [i.value for i in persons[-1].get('friends', dbsession)] == [p1.id, 1]
    
    def test_raise_on_non_unique(self, dbsession):
        p1 = {
            'name': 'Jack', 
            'nickname': 'jack',  # <-- already exists in db
            'age': 10,
            'friends': []
        }
        with pytest.raises(UniqueValueException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_no_raise_on_non_unique_value_if_it_is_deleted(self, dbsession):
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 1

        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        p1 = {
            'name': 'Jack',  
            'nickname': 'jack', # <-- already exists in db, but for deleted entity
            'age': 10,
            'friends': []
        }
        e = create_entity(dbsession, schema_id=1, data=p1)
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 2
        assert [i.entity_id for i in jacks] == [1, e.id]

    def test_raise_on_schema_doesnt_exist(self, dbsession):
        p = {
            'name': 'Some Name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingSchemaException):
            create_entity(dbsession, schema_id=99999, data=p)

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        p = {
            'name': 'Some name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        with pytest.raises(AttributeNotDefinedException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_value_cast(self, dbsession):
        p = {
            'name': 'Some name',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [1],
        }
        with pytest.raises(ValueError):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession):
        p = {
            'name': 'Some name',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [1],
        }
        with pytest.raises(NotListedAttributeException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        p1 = {
            'name': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_fk_entity_is_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        p1 = {
            'name': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_fk_entity_from_wrong_schema(self, dbsession):
        schema = Schema(name='Test', slug='test')
        dbsession.add(schema)
        dbsession.flush()
        entity = Entity(schema_id=schema.id, name='test')
        dbsession.add(entity)
        dbsession.flush()

        p1 = {
            'name': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [entity.id]
        }
        with pytest.raises(WrongSchemaToBindException):
            create_entity(dbsession, schema_id=1, data=p1)


class TestEntityUpdate:
    pass


class TestEntityDelete:
    def test_delete(self, dbsession):
        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        delete_entity(dbsession, entity_id=e.id)
        
        entities = dbsession.execute(select(Entity)).scalars().all()
        assert len(entities) == 2
        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        assert e.deleted

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, entity_id=9999999999)

    def test_raise_on_already_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, entity_id=1)
        