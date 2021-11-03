from datetime import datetime

import pytest
from sqlalchemy import select, update

from ..models import *
from ..dynamic_routes import *
from .. import load_schemas


def test_load_schema_data(dbsession, client):
    schemas = load_schemas()
    assert len(schemas) == 1

    s = schemas[0]
    assert s.name == 'Person'


def test_routes_were_generated(dbsession, client):
    routes = [
        '/person/{id_or_slug}',
        '/person',
        '/attributes',
        '/attributes/{attr_id}',
        '/schemas/{id_or_slug}',
        '/schemas/{id_or_slug}',
        '/schemas'
    ]
    assert all([i in [route.path for route in client.app.routes] for i in routes])


class TestRouteGetEntity:
    def test_get_entity(self, dbsession, client):
        data = {
            'id': 1,
            'slug': 'Jack',
            'name': 'Jack',
            'deleted': False,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack'
        }
        response = client.get('/person/1')
        assert response.status_code == 200
        assert  response.json() == data

        response = client.get(f'/person/Jack')
        assert response.status_code == 200
        assert  response.json() == data

    def test_raise_on_entity_doesnt_exist(self, dbsession, client):
        response = client.get('/person/99999999')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession, client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([e, s])
        dbsession.commit()
        
        response = client.get(f'/person/{e.id}')
        assert response.status_code == 409
        assert "doesn't belong to specified Schema" in response.json()['detail']

class TestRouteGetEntities:
    @pytest.fixture
    def jack(self):
        return {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}
    
    @pytest.fixture
    def jane(self):
        return {'age': 12, 'id': 2, 'deleted': False, 'slug': 'Jane', 'name': 'Jane'}

    @pytest.fixture
    def jack_del(self):
        return {'age': 10, 'id': 1, 'deleted': True, 'slug': 'Jack', 'name': 'Jack'}

    def test_get_entities(self, dbsession, client):
        data = [
            {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}, 
            {'age': 12, 'id': 2, 'deleted': False, 'slug': 'Jane', 'name': 'Jane'}
        ]
        response = client.get(f'/person/')
        assert response.status_code == 200
        assert response.json()['entities'] == data

    def test_get_deleted_only(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.commit()

        data = [{'age': 12, 'id': 2, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}]
        response = client.get(f'/person?deleted_only=True')
        assert response.status_code == 200
        assert response.json()['entities'] == data

    def test_get_all(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.commit()

        data = {'total': 2, 'entities': [
            {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}, 
            {'age': 12, 'id': 2, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}
        ]}
        response = client.get(f'/person?all=True')
        assert response.status_code == 200
        assert response.json() == data

        response = client.get(f'/person?all=True&deleted_only=True')
        assert response.status_code == 200
        assert response.json() == data

    def test_get_all_fields(self, dbsession, client):
        data =  {'total': 2, 'entities': [
            {
                'age': 10, 
                'born': None, 
                'friends': [], 
                'nickname': 'jack', 
                'id': 1, 
                'deleted': False, 
                'slug': 'Jack',
                'name': 'Jack'
            }, 
            {
                'age': 12, 
                'born': None, 
                'friends': [1], 
                'nickname': 'jane', 
                'id': 2, 'deleted': False, 
                'slug': 'Jane', 
                'name': 'Jane'
             }
        ]}
        response = client.get(f'/person?all_fields=True')
        assert response.status_code == 200
        assert response.json() == data

    def test_offset_and_limit(self, dbsession, client):
        jack = {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}
        jane = {'age': 12, 'id': 2, 'deleted': False, 'slug': 'Jane', 'name': 'Jane'}

        response = client.get(f'/person?limit=1')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': [jack]}

        response = client.get(f'/person?limit=1&offset=1')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': [jane]}

        response = client.get(f'/person?offset=10')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': []}

    
    @pytest.mark.parametrize(['q', 'resp'], [
        ('age=10',           ['jack']),
        ('age.lt=10',        []),
        ('age.eq=10',        ['jack']),
        ('age.gt=10',        ['jane']),
        ('age.le=10',        ['jack']),
        ('age.ne=10',        ['jane']),
        ('age.ge=10',        ['jack', 'jane']),
        ('name=Jane',        ['jane']),
        ('nickname=jane',    ['jane']),
        ('nickname.ne=jack', ['jane']),
    ])
    def test_get_with_filter(self, dbsession, client, request, q, resp):
        ents = [request.getfixturevalue(i) for i in resp]
        resp =  {'total': len(ents), 'entities': ents}
        response = client.get(f'/person?{q}')
        assert response.json() == resp

    def test_get_with_multiple_filters_for_same_attr(self, dbsession, client, jane):
        response = client.get('/person?age.gt=9&age.ne=10')
        assert response.json()['entities'] == [jane]

        response = client.get('/person?age.gt=9&age.ne=10&age.lt=12')
        assert response.json()['entities'] == []

    @pytest.mark.parametrize(['q', 'resp'], [
        ('age.gt=9&name.ne=Jack',               ['jane']),
        ('name=Jack&name.ne=Jack',              []),
        ('nickname.ne=jane&name.ne=Jack',       []),
        ('age.gt=9&age.ne=10&nickname.ne=jane', [])
    ])
    def test_get_with_multiple_filters(self, dbsession, client, request, q, resp):
        resp = [request.getfixturevalue(i) for i in resp]
        response = client.get(f'/person?{q}')
        assert response.json()['entities'] == resp

    def test_get_with_filters_and_offset_limit(self, dbsession, client, jack, jane):
        response = client.get('/person?age.gt=0&age.lt=20&limit=1')
        assert response.json()['entities'] == [jack]

        response = client.get('/person?age.gt=0&age.lt=20&limit=1&offset=1')
        assert response.json()['entities'] == [jane]

        response = client.get('/person?age.gt=0&age.lt=20&offset=2')
        assert response.json()['entities'] == []

    @pytest.mark.parametrize(['q', 'resp'], [
        ('age.gt=0&age.lt=20',                            ['jane']),
        ('offset=1&age.gt=0&age.lt=20',                   []),
        ('all=True&age.gt=0&age.lt=20',                   ['jack_del', 'jane']),
        ('deleted_only=True&age.gt=0&age.lt=20',          ['jack_del']),
        ('deleted_only=true&offset=1&age.gt=0&age.lt=20', []),
    ])
    def test_get_with_filters_and_deleted(self, dbsession, client, request, q, resp):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jack').values(deleted=True))
        dbsession.commit()
        resp = [request.getfixturevalue(i) for i in resp]
        response = client.get(f'/person?{q}')
        assert response.json()['entities'] == resp

    def test_ignore_invalid_filter(self, dbsession, client, jack, jane):
        response = client.get('/person?age.gt=0&age.lt=20&qwe.rty=123')
        assert response.json()['entities'] == [jack, jane]

        response = client.get('/person?age.gt=0&age.lt=20&friends.lt=1234')
        assert response.json()['entities'] == [jack, jane]

        response = client.get('/person?age.qwe=1234')
        assert response.json()['entities'] == [jack, jane]

    def test_ignore_filters_for_list_and_fk(self, dbsession, client, jack, jane):
        response = client.get('/person?friends=1')
        assert response.json()['entities'] == [jack, jane]

class TestRouteCreateEntity:
    def test_create(self, dbsession, client):
        p1 = {
            'name': 'mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        response = client.post(f'/person', json=p1)
        assert response.json() == {'id': 3, 'slug': 'Mike', 'name': 'mike', 'deleted': False}
        
        mike = dbsession.execute(select(Entity).where(Entity.id == 3)).scalar()
        assert mike.get('nickname', dbsession).value == 'mike'
        assert mike.get('age', dbsession).value == 10
        assert mike.get('friends', dbsession) == []

        p2 = {
            'name': 'john',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [3, 1],
            'born': '2021-10-20T13:52:17',
        }
        response = client.post(f'/person', json=p2)
        assert response.json() == {'id': 4, 'slug': 'John', 'name': 'john', 'deleted': False}

        john = dbsession.execute(select(Entity).where(Entity.id == 4)).scalar()
        assert john.get('nickname', dbsession).value == 'john'
        assert john.get('age', dbsession).value == 10
        assert [i.value for i in john.get('friends', dbsession)] == [3, 1]
        assert john.get('born', dbsession).value == datetime(2021, 10, 20, 13, 52, 17)

    def test_raise_on_non_unique_slug(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Jack', 
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']

    def test_no_raise_on_same_slug_in_different_schemas(self, dbsession):
        s = Schema(name='Test', slug='test')
        dbsession.add(s)
        dbsession.commit()

        from .conftest import client_
        client = client_(engine=dbsession.get_bind())

        data = {'slug': 'Jack', 'name': 'name'}
        response = client.post(f'/test', json=data)
        assert response.status_code == 200

    def test_raise_on_invalid_slug(self, dbsession, client):
        p1 = {
            'slug': '-Jake-', 
            'nickname': 'jackie',
            'age': 10,
            'friends': []
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 422
        assert 'is invalid value for slug field' in response.json()['detail'][0]['msg']

    def test_raise_on_non_unique_field(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Jake', 
            'nickname': 'jack',  # <-- already exists in db
            'age': 10,
            'friends': []
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 409
        assert 'Got non-unique value for field' in response.json()['detail']

    
    def test_no_raise_on_non_unique_value_if_it_is_deleted(self, dbsession, client):
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 1

        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        dbsession.commit()
        p1 = {
            'name': 'name',
            'slug': 'Jackie',  
            'nickname': 'jack', # <-- already exists in db, but for deleted entity
            'age': 10,
            'friends': []
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 200

    def test_raise_on_attr_doesnt_exist(self, dbsession, client):
        p = {
            'name': 'name',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        response = client.post(f'/person', json=p)
        assert response.status_code == 422
        assert 'extra fields not permitted' in response.json()['detail'][0]['msg']

    def test_raise_on_value_cast(self, dbsession, client):
        p = {
            'name': 'name',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 'INVALID VALUE',
            'friends': [1],
        }
        response = client.post(f'/person', json=p)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_passed_list_for_single_value_attr(self, dbsession, client):
        p = {
            'name': 'name',
            'slug': 'Some name',
            'nickname': 'somename',
            'age': [1, 2, 3],
            'friends': [1],
        }
        response = client.post(f'/person', json=p)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_is_deleted(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        dbsession.commit()
        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_from_wrong_schema(self, dbsession, client):
        schema = Schema(name='Test', slug='test')
        entity = Entity(schema=schema, slug='test', name='test')
        dbsession.add_all([schema, entity])
        dbsession.commit()

        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [entity.id]
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 422
        assert 'got instead entity' in response.json()['detail']
        
    def test_raise_on_slug_not_provided(self, dbsession, client):
        p1 = {
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 422
        assert 'field required' in response.json()['detail'][0]['msg']

    def test_raise_on_required_field_not_provided(self, dbsession, client):
        p1 = {
            'slug': 'Mike',
            'friends': [1]
        }
        response = client.post(f'/person', json=p1)
        assert response.status_code == 422
        assert 'field required' in response.json()['detail'][0]['msg']

    
class TestRouteUpdateEntity:
    def test_update(self, dbsession, client):
        time = datetime.now()
        data = {
            'name': 'test',
            'slug': 'test',
            'nickname': None,
            'born': '2021-10-20T13:52:17',
            'friends': [1, 2],
        }
        response = client.put('person/1', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'slug': 'test', 'name': 'test', 'deleted': False}

        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        assert e.name == 'test'
        assert e.slug == 'test'
        assert e.get('age', dbsession).value == 10
        assert e.get('born', dbsession).value == datetime(2021, 10, 20, 13, 52, 17)
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
        response = client.put('person/Jane', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 2, 'slug': 'test2', 'name': 'Jane', 'deleted': False}
        
        e = dbsession.execute(select(Entity).where(Entity.id == 2)).scalar()
        assert e.slug == 'test2'
        assert e.name == 'Jane'
        assert e.get('nickname', dbsession).value == 'test'
        nicknames = dbsession.execute(
            select(ValueStr)
            .where(Attribute.name == 'nickname')
            .join(Attribute)
        ).scalars().all()
        assert len(nicknames) == 1, "nickname for entity 2 wasn't deleted from database"

    def test_raise_on_entity_doesnt_exist(self, dbsession, client):
        response = client.put('person/99999999999', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

        response = client.put('person/qwertyuiop', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()
        response = client.put('person/test', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_schema_is_deleted(self, dbsession, client):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        response = client.put('person/1', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_entity_already_exists(self, dbsession, client):
        data = {'slug': 'Jane'}
        response = client.put('person/1', json=data)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']

    def test_no_raise_on_changing_to_same_slug(self, dbsession, client):
        data = {'slug': 'Jack'}
        response = client.put('person/1', json=data)
        assert response.status_code == 200

    def test_raise_on_attribute_not_defined_on_schema(self, dbsession, client):
        data = {'not_existing_attr': 50000}
        response = client.put('person/1', json=data)
        assert response.status_code == 422
        assert 'extra fields not permitted' in response.json()['detail'][0]['msg']
        
        data = {'address': 1234}
        response = client.put('person/1', json=data)
        assert response.status_code == 422
        assert 'extra fields not permitted' in response.json()['detail'][0]['msg']

    def test_raise_on_invalid_slug(self, dbsession, client):
        p1 = {
            'slug': '-Jake-', 
        }
        response = client.put(f'/person/1', json=p1)
        assert response.status_code == 422
        assert 'is invalid value for slug field' in response.json()['detail'][0]['msg']

    def test_raise_on_deleting_required_value(self, dbsession, client):
        data = {'age': None}
        response = client.put('person/1', json=data)
        assert response.status_code == 422
        assert 'Missing required field' in response.json()['detail']

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession, client):
        data = {'age': [1, 2, 3, 4, 5]}
        response = client.put('person/1', json=data)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, client):
        data = {'friends': [9999999999]}
        response = client.put('person/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession, client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()
        
        data = {'friends': [e.id]}
        response = client.put('person/1', json=data)
        assert response.status_code == 422
        assert "got instead entity" in response.json()['detail']

    def test_raise_on_non_unique_value(self, dbsession, client):
        data = {'nickname': 'jane'}
        response = client.put('person/1', json=data)
        assert response.status_code == 409
        assert 'Got non-unique value' in response.json()['detail']

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jane').values(deleted=True))
        dbsession.commit()

        data = {'nickname': 'jane'}
        response = client.put('person/Jack', json=data)
        assert response.status_code == 200
        
        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'


class TestRouteDeleteEntity:
    @pytest.mark.parametrize('entity', [1, 'Jack'])
    def test_delete(self, dbsession, client, entity):
        response = client.delete(f'/person/{entity}')
        assert response.json() == {'id': 1, 'slug': 'Jack', 'name': 'Jack', 'deleted': True}

        entities = dbsession.execute(select(Entity)).scalars().all()
        assert len(entities) == 2
        e = dbsession.execute(select(Entity).where(Entity.id == 1)).scalar()
        assert e.deleted

    @pytest.mark.parametrize('entity', [1234567, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, client, entity):
        response = client.delete(f'/person/{entity}')
        assert response.status_code == 404

    @pytest.mark.parametrize('entity', [1, 'Jack'])
    def test_raise_on_already_deleted(self, dbsession, client, entity):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        dbsession.commit()
        response = client.delete(f'/person/{entity}')
        assert response.status_code == 404