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
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        p1 = create_entity(dbsession, schema_id=1, data=p1)
        p2 = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [p1.id, 1],
            'born': born
        }
        p2 = create_entity(dbsession, schema_id=1, data=p2)

        persons = dbsession.execute(select(Entity).where(Entity.schema_id == 1)).scalars().all()
        assert len(persons) == 4
        assert persons[-1].name == 'John'
        assert persons[-1].slug == 'John'
        assert persons[-1].get('nickname', dbsession).value == 'john'
        assert persons[-1].get('age', dbsession).value == 10
        assert persons[-1].get('born', dbsession).value == born
        assert isinstance(persons[-1].get('age', dbsession), ValueInt)
        assert [i.value for i in persons[-1].get('friends', dbsession)] == [p1.id, 1]
    
    def test_raise_on_non_unique_slug(self, dbsession):
        p1 = {
            'name': 'Jack',
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

        data = {'slug': 'Jack', 'name': 'Jack'}
        create_entity(dbsession, schema_id=s.id, data=data)

    def test_raise_on_non_unique_field(self, dbsession):
        p1 = {
            'name': 'Jack',
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
            'name': 'Jack',
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
            'name': 'somename',
            'slug': 'Some Name',
            'nickname': 'somename',
            'age': 10,
            'friends': [1]
        }
        with pytest.raises(MissingSchemaException):
            create_entity(dbsession, schema_id=99999, data=p)

    def test_raise_on_attr_doesnt_exist(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        with pytest.raises(AttributeNotDefinedException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_value_cast(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [1],
        }
        with pytest.raises(ValueError):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession):
        p = {
            'name': 'somename',
            'slug': 'Somename',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [1],
        }
        with pytest.raises(NotListedAttributeException):
            create_entity(dbsession, schema_id=1, data=p)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        p1 = {
            'name': 'mike',
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
            'name': 'mike',
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
        entity = Entity(schema_id=schema.id, slug='test', name='test')
        dbsession.add(entity)
        dbsession.flush()

        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [entity.id]
        }
        with pytest.raises(WrongSchemaToBindException):
            create_entity(dbsession, schema_id=1, data=p1)

    def test_raise_on_slug_not_provided(self, dbsession):
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
            'name': 'mike',
            'friends': [1]
        }
        with pytest.raises(RequiredFieldException):
            create_entity(dbsession, schema_id=1, data=p1)


class TestEntityRead:
    def test_get_entity(self, dbsession):
        jack = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        expected = {
            'id': jack.id,
            'name': jack.name,
            'slug': jack.slug,
            'deleted': jack.deleted,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack'
        }
        data = get_entity(dbsession, id_or_slug=jack.id, schema=jack.schema)
        assert data == expected

        data = get_entity(dbsession, id_or_slug=jack.slug, schema=jack.schema)
        assert data == expected

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            get_entity(dbsession, id_or_slug=9999999999, schema=Schema())

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession):
        s = Schema(name='test', slug='test')
        dbsession.add(s)
        dbsession.flush()
        with pytest.raises(MismatchingSchemaException):
            get_entity(dbsession, id_or_slug=1, schema=s)

    def test_get_entities(self, dbsession):
        # test default behavior: return not deleted entities
        e = Entity(slug='Test', name='test', schema_id=1, deleted=True)
        dbsession.add(e)
        dbsession.flush()

        schema = dbsession.execute(select(Schema).where(Schema.id == 1)).scalar()
        ents = get_entities(dbsession, schema=schema)
        
        assert len(ents) == 2

        default_field_list = {'id', 'slug', 'deleted', 'age', 'name'}
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
        assert ent['name'] == 'Jane'
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
    def test_update(self, dbsession):
        time = datetime.now()
        data = {
            'slug': 'test',
            'nickname': None,
            'born': time,
            'friends': [1, 2],
        }
        update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)
        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        assert e.slug == 'test'
        assert e.get('age', dbsession).value == 10
        assert e.get('born', dbsession).value == time
        assert [i.value for i in e.get('friends', dbsession)] == [1, 2]
        assert e.get('nickname', dbsession) == None
        nicknames = dbsession.execute(
            select(ValueStr)
            .where(Attribute.name == 'nickname')
            .join(Attribute)
        ).scalars().all()
        assert len(nicknames) == 1, "nickname for entity 1 wasn't deleted from database"

        data = {
            'slug': 'test2',
            'nickname': 'test'
        }
        update_entity(dbsession, id_or_slug='Jane', schema_id=1, data=data)
        e = dbsession.execute(select(Entity).where(Entity.id == 2)).scalar()
        assert e.slug == 'test2'
        assert e.get('nickname', dbsession).value == 'test'
        nicknames = dbsession.execute(
            select(ValueStr)
            .where(Attribute.name == 'nickname')
            .join(Attribute)
        ).scalars().all()
        assert len(nicknames) == 1, "nickname for entity 2 wasn't deleted from database"

    def test_raise_on_entity_doesnt_exist(self, dbsession):
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=9999, schema_id=1, data={})

        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='qwertyuiop', schema_id=1, data={})

        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug='test', schema_id=1, data={})

    def test_raise_on_schema_is_deleted(self, dbsession):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        with pytest.raises(MissingSchemaException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data={})

    def test_raise_on_entity_already_exists(self, dbsession):
        data = {'slug': 'Jane'}
        with pytest.raises(EntityExistsException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_no_raise_on_changing_to_same_slug(self, dbsession):
        data = {'slug': 'Jack'}
        update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_attribute_not_defined_on_schema(self, dbsession):
        data = {'not_existing_attr': 50000}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)
        dbsession.rollback()
        
        data = {'address': 1234}
        with pytest.raises(AttributeNotDefinedException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_deleting_required_value(self, dbsession):
        data = {'age': None}
        with pytest.raises(RequiredFieldException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession):
        data = {'age': [1, 2, 3, 4, 5]}
        with pytest.raises(NotListedAttributeException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession):
        data = {'friends': [9999999999]}
        with pytest.raises(MissingEntityException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.flush()

        data = {'friends': [e.id]}
        with pytest.raises(WrongSchemaToBindException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_raise_on_non_unique_value(self, dbsession):
        data = {'nickname': 'jane'}
        with pytest.raises(UniqueValueException):
            update_entity(dbsession, id_or_slug=1, schema_id=1, data=data)

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jane').values(deleted=True))
        data = {'nickname': 'jane'}
        update_entity(dbsession, id_or_slug='Jack', schema_id=1, data=data)
        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'


class TestEntityDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'Jack'])
    def test_delete(self, dbsession, id_or_slug):
        delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)
        
        entities = dbsession.execute(select(Entity)).scalars().all()
        assert len(entities) == 2
        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        assert e.deleted

    @pytest.mark.parametrize('id_or_slug', [1234567, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, id_or_slug):
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)

    @pytest.mark.parametrize('id_or_slug', [1, 'Jack'])
    def test_raise_on_already_deleted(self, dbsession, id_or_slug):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        with pytest.raises(MissingEntityException):
            delete_entity(dbsession, id_or_slug=id_or_slug, schema_id=1)
        