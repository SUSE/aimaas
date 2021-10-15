from datetime import datetime
import pydantic

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
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        p1 = create_entity(dbsession, schema_id=1, data=p1)
        p2 = {
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [p1.id, 1],
            'born': born.timestamp()
        }
        p2 = create_entity(dbsession, schema_id=1, data=p2)

        persons = dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
        assert len(persons) == 4
        assert persons[-1].slug == 'John'
        assert persons[-1].get('nickname', dbsession).value == 'john'
        assert persons[-1].get('age', dbsession).value == 10
        assert persons[-1].get('born', dbsession).value == born
        assert isinstance(persons[-1].get('age', dbsession), ValueInt)
        assert [i.value for i in persons[-1].get('friends', dbsession)] == [p1.id, 1]
    
    def test_raise_on_non_unique_slug(self, dbsession):
        p1 = {
            'slug': 'Jack', 
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        with pytest.raises(EntityExistsException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_no_raise_on_same_slug_in_different_schemas(self, dbsession):
        s = Schema(name='Test', slug='test')
        dbsession.add(s)
        dbsession.flush()

        data = {'slug': 'Jack'}
        create_entity(dbsession, schema_id=s.id, data=data)

    def test_raise_on_non_unique_field(self, dbsession):
        p1 = {
            'slug': 'Jake', 
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
            'slug': 'Jackie',  
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
            'slug': 'Some Name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingSchemaException):
            create_entity(dbsession, schema_id=99999, data=p)

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        p = {
            'slug': 'Some name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        with pytest.raises(AttributeNotDefinedException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_value_cast(self, dbsession):
        p = {
            'slug': 'Some name',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [1],
        }
        with pytest.raises(ValueError):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession):
        p = {
            'slug': 'Some name',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [1],
        }
        with pytest.raises(NotListedAttributeException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        p1 = {
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        with pytest.raises(MissingEntityException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_fk_entity_is_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        p1 = {
            'slug': 'Mike',
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
        entity = Entity(schema_id=schema.id, slug='test')
        dbsession.add(entity)
        dbsession.flush()

        p1 = {
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [entity.id]
        }
        with pytest.raises(WrongSchemaToBindException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_name_not_provided(self, dbsession):
        p1 = {
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_required_field_not_provided(self, dbsession):
        p1 = {
            'slug': 'Mike',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=1, data=p1)


class TestEntityRead:
    def test_get_entity(self, dbsession):
        jack = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        expected = {
            'id': jack.id,
            'slug': jack.slug,
            'deleted': jack.deleted,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack'
        }
        data = get_entity(dbsession, entity_id=jack.id, schema=jack.schema)
        assert data == expected

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, entity_id=9999999999, schema=Schema())

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession):
        s = Schema(name='test', slug='test')
        dbsession.add(s)
        dbsession.flush()
        with pytest.raises(MismatchingSchemaException):
            get_entity(dbsession, entity_id=1, schema=s)

    def test_get_entities(self, dbsession):
        # test default behavior: return not deleted entities
        e = Entity(slug='Test', schema_id=1, deleted=True)
        dbsession.add(e)
        dbsession.flush()

        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        ents = get_entities(dbsession, schema=schema)
        
        assert len(ents) == 2

        default_field_list = {'id', 'slug', 'deleted', 'age'}
        ent = ents[1]
        assert set(ent.keys()) == default_field_list
        assert ent['id'] == 2
        assert ent['slug'] == 'Jane'
        assert ent['deleted'] == False
        assert ent['age'] == 12

    def test_get_deleted_only(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.flush()

        ents = get_entities(dbsession, schema=schema, deleted_only=True)
        assert len(ents) == 1
        assert ents[0]['id'] == 2
    
    def test_get_all(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.flush()

        ents = get_entities(dbsession, schema=schema, all=True)
        assert len(ents) == 2
        assert not ents[0]['deleted'] and ents[1]['deleted']

    def test_get_all_fields(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        ents = get_entities(dbsession, schema=schema, all_fields=True)
        assert len(ents) == 2
        
        ent = ents[1]
        assert ent['id'] == 2
        assert ent['slug'] == 'Jane'
        assert ent['deleted'] == False
        assert ent['age'] == 12
        assert ent['born'] == None
        assert ent['friends'] == [1]
        assert ent['nickname'] == 'jane'

    def test_offset_and_limit(self, dbsession):
        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        
        ents = get_entities(dbsession, schema=schema, limit=1)
        assert len(ents) == 1
        assert ents[0]['id'] == 1

        ents = get_entities(dbsession, schema=schema, limit=1, offset=1)
        assert len(ents) == 1
        assert ents[0]['id'] == 2

        ents = get_entities(dbsession, schema=schema, offset=10)
        assert len(ents) == 0


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
        