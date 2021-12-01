from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select, update

from ..models import *
from ..dynamic_routes import *
from .. import load_schemas
from .test_crud_entity import (
    asserts_after_entities_create,
    asserts_after_entities_update,
    asserts_after_entity_delete
)
from .test_traceability_entity import (
    asserts_after_submitting_entity_create_request,
    asserts_after_applying_entity_create_request,
    asserts_after_submitting_entity_update_request,
    asserts_after_applying_entity_update_request,
    asserts_after_submitting_entity_delete_request,
    asserts_after_applying_entity_delete_request
)


def test_load_schema_data(dbsession, client):
    schemas = load_schemas()
    assert len(schemas) == 1

    s = schemas[0]
    assert s.name == 'Person'


def test_routes_were_generated(dbsession, client):
    routes = [
        '/dynamic/person/{id_or_slug}',
        '/dynamic/person',
        '/attributes',
        '/attributes/{attr_id}',
        '/schemas/{id_or_slug}',
        '/schemas/{id_or_slug}',
        '/schemas'
    ]
    assert all([i in [route.path for route in client.app.routes] for i in routes])

class TestRouteCreateEntity:
    def assert_no_change_requests_appeared(self, db: Session):
        assert db.execute(select(Change)).scalar() is None
        assert db.execute(select(EntityCreate)).scalar() is None
        assert db.execute(select(ValueUpdate)).scalar() is None

    def test_create_without_review(self, dbsession, client):
        p1 = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        response = client.post(f'/dynamic/person', json=p1)
        json = response.json()
        mike_id = json.pop('id')
        assert json == {'slug': 'Mike', 'name': 'Mike', 'deleted': False}

        asserts_after_applying_entity_create_request(dbsession, change_id=1)

        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
        p2 = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [mike_id, 1],
            'born': str(born),
        }
        response = client.post(f'/dynamic/person', json=p2)
        json = response.json()
        john_id = json.pop('id')
        assert json == {'slug': 'John', 'name': 'John', 'deleted': False}
        
        asserts_after_applying_entity_create_request(dbsession, change_id=2)

        p3 = {
            'name': 'Pumpkin Jack',
            'slug': 'pumpkin-jack',
            'nickname': 'pumpkin',
            'age': 38,
            'friends': [mike_id, john_id],
            'born': str(tz_born)
        }
        response = client.post(f'/dynamic/person', json=p3)
        json = response.json()
        del json['id']
        assert json == {'slug': 'pumpkin-jack', 'name': 'Pumpkin Jack', 'deleted': False}

        asserts_after_entities_create(dbsession)
        asserts_after_applying_entity_create_request(dbsession, change_id=3)

    def test_raise_on_non_unique_slug(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Jack', 
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_no_raise_on_same_slug_in_different_schemas(self, dbsession):
        s = Schema(name='Test', slug='test')
        dbsession.add(s)
        dbsession.commit()

        from .conftest import client_
        client = client_(engine=dbsession.get_bind())

        data = {'slug': 'Jack', 'name': 'name'}
        response = client.post(f'/dynamic/test', json=data)
        assert response.status_code == 200
        
        changes = dbsession.execute(select(Change)).scalars().all()
        ent_creates = dbsession.execute(select(EntityCreate)).scalars().all()
        val_creates = dbsession.execute(select(ValueUpdate)).scalars().all()
        assert len(changes) == 1
        assert len(ent_creates) == 1
        assert not val_creates
        entity = dbsession.execute(select(Entity).where(Entity.schema_id == 2)).scalar()
        assert entity.slug == 'Jack' and entity.name == 'name'

    def test_raise_on_non_unique_field(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Jake', 
            'nickname': 'jack',  # <-- already exists in db
            'age': 10,
            'friends': []
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 409
        assert 'Got non-unique value for field' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

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
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 200

        changes = dbsession.execute(select(Change)).scalars().all()
        ent_creates = dbsession.execute(select(EntityCreate)).scalars().all()
        val_creates = dbsession.execute(select(ValueUpdate)).scalars().all()
        assert len(changes) == 1
        assert len(ent_creates) == 1
        assert len(val_creates) == 5  # 3 passed + 2 optional not passed
        entity = dbsession.execute(select(Entity).where(Entity.slug == 'Jackie')).scalar()
        assert entity is not None
    
    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, client):
        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

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
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

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
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 422
        assert 'got instead entity' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)


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
            'nickname': 'jack',
            'fav_color': ['red', 'blue']
        }
        response = client.get('/dynamic/person/1')
        assert response.status_code == 200
        assert  response.json() == data

        response = client.get(f'/dynamic/person/Jack')
        assert response.status_code == 200
        assert  response.json() == data

    def test_raise_on_entity_doesnt_exist(self, dbsession, client):
        response = client.get('/dynamic/person/99999999')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession, client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([e, s])
        dbsession.commit()
        
        response = client.get(f'/dynamic/person/{e.id}')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']


class TestRouteGetEntities:
    # TODO tests for ordering
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
        response = client.get(f'/dynamic/person/')
        assert response.status_code == 200
        assert response.json()['entities'] == data

    def test_get_deleted_only(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.commit()

        data = [{'age': 12, 'id': 2, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}]
        response = client.get(f'/dynamic/person?deleted_only=True')
        assert response.status_code == 200
        assert response.json()['entities'] == data

    def test_get_all(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.id == 2).values(deleted=True))
        dbsession.commit()

        data = {'total': 2, 'entities': [
            {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}, 
            {'age': 12, 'id': 2, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}
        ]}
        response = client.get(f'/dynamic/person?all=True')
        assert response.status_code == 200
        assert response.json() == data

        response = client.get(f'/dynamic/person?all=True&deleted_only=True')
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
                'name': 'Jack',
                'fav_color': ['red', 'blue']
            }, 
            {
                'age': 12, 
                'born': None, 
                'friends': [1], 
                'nickname': 'jane', 
                'id': 2, 'deleted': False, 
                'slug': 'Jane', 
                'name': 'Jane',
                'fav_color': ['red', 'black']
             }
        ]}
        response = client.get(f'/dynamic/person?all_fields=True')
        assert response.status_code == 200
        assert response.json() == data

    def test_offset_and_limit(self, dbsession, client):
        jack = {'age': 10, 'id': 1, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'}
        jane = {'age': 12, 'id': 2, 'deleted': False, 'slug': 'Jane', 'name': 'Jane'}

        response = client.get(f'/dynamic/person?limit=1')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': [jack]}

        response = client.get(f'/dynamic/person?limit=1&offset=1')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': [jane]}

        response = client.get(f'/dynamic/person?offset=10')
        assert response.status_code == 200
        assert response.json() ==  {'total': 2, 'entities': []}

    
    @pytest.mark.parametrize(['q', 'resp'], [
        ('age=10',               ['jack']),
        ('age.lt=10',            []),
        ('age.eq=10',            ['jack']),
        ('age.gt=10',            ['jane']),
        ('age.le=10',            ['jack']),
        ('age.ne=10',            ['jane']),
        ('age.ge=10',            ['jack', 'jane']),
        ('name=Jane',            ['jane']),
        ('nickname=jane',        ['jane']),
        ('nickname.ne=jack',     ['jane']),
        ('nickname.regexp=^ja',  ['jack', 'jane']),
        ('nickname.contains=ne', ['jane']),
        ('fav_color.eq=black',   ['jane']),
        ('fav_color.ne=black',   ['jack', 'jane'])  # still returns both even though Jane has black fav_color, but also has red
    ])
    def test_get_with_filter(self, dbsession, client, request, q, resp):
        ents = [request.getfixturevalue(i) for i in resp]
        resp =  {'total': len(ents), 'entities': ents}
        response = client.get(f'/dynamic/person?{q}')
        assert response.json() == resp

    def test_get_with_multiple_filters_for_same_attr(self, dbsession, client, jane):
        response = client.get('/dynamic/person?age.gt=9&age.ne=10')
        assert response.json()['entities'] == [jane]

        response = client.get('/dynamic/person?age.gt=9&age.ne=10&age.lt=12')
        assert response.json()['entities'] == []

    @pytest.mark.parametrize(['q', 'resp'], [
        ('age.gt=9&name.ne=Jack',               ['jane']),
        ('name=Jack&name.ne=Jack',              []),
        ('nickname.ne=jane&name.ne=Jack',       []),
        ('age.gt=9&age.ne=10&nickname.ne=jane', [])
    ])
    def test_get_with_multiple_filters(self, dbsession, client, request, q, resp):
        resp = [request.getfixturevalue(i) for i in resp]
        response = client.get(f'/dynamic/person?{q}')
        assert response.json()['entities'] == resp

    def test_get_with_filters_and_offset_limit(self, dbsession, client, jack, jane):
        response = client.get('/dynamic/person?age.gt=0&age.lt=20&limit=1')
        assert response.json()['entities'] == [jack]

        response = client.get('/dynamic/person?age.gt=0&age.lt=20&limit=1&offset=1')
        assert response.json()['entities'] == [jane]

        response = client.get('/dynamic/person?age.gt=0&age.lt=20&offset=2')
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
        response = client.get(f'/dynamic/person?{q}')
        assert response.json()['entities'] == resp

    def test_ignore_invalid_filter(self, dbsession, client, jack, jane):
        response = client.get('/dynamic/person?age.gt=0&age.lt=20&qwe.rty=123')
        assert response.json()['entities'] == [jack, jane]

        response = client.get('/dynamic/person?age.gt=0&age.lt=20&friends.lt=1234')
        assert response.json()['entities'] == [jack, jane]

        response = client.get('/dynamic/person?age.qwe=1234')
        assert response.json()['entities'] == [jack, jane]

    def test_ignore_filters_for_fk(self, dbsession, client, jack, jane):
        response = client.get('/dynamic/person?friends=1')
        assert response.json()['entities'] == [jack, jane]


class TestRouteUpdateEntity:
    def assert_no_change_requests_appeared(self, db: Session):
        assert db.execute(select(Change)).scalar() is None
        assert db.execute(select(EntityUpdate)).scalar() is None
        assert db.execute(select(ValueUpdate)).scalar() is None

    def test_update_without_review(self, dbsession: Session, client):
        data = {
            'name': 'test',
            'slug': 'test',
            'nickname': None,
            'born': '2021-10-20T13:52:17+03',
            'friends': [1, 2],
        }
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'slug': 'test', 'name': 'test', 'deleted': False}
        asserts_after_applying_entity_update_request(dbsession, change_id=1)

        born_utc = datetime(2021, 10, 20, 10, 52, 17, tzinfo=timezone.utc)
       
        data = {
            'slug': 'test2',
            'nickname': 'test'
        }
        response = client.put('/dynamic/person/Jane', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': 2, 'slug': 'test2', 'name': 'Jane', 'deleted': False}
        asserts_after_applying_entity_update_request(dbsession, change_id=2)
        asserts_after_entities_update(dbsession, born_time=born_utc)

    def test_raise_on_entity_doesnt_exist(self, dbsession, client):
        response = client.put('/dynamic/person/99999999999', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

        response = client.put('/dynamic/person/qwertyuiop', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()
        response = client.put('/dynamic/person/test', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_schema_is_deleted(self, dbsession, client):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        response = client.put('/dynamic/person/1', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)
        
    def test_raise_on_entity_already_exists(self, dbsession, client):
        data = {'slug': 'Jane'}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_no_raise_on_changing_to_same_slug(self, dbsession, client):
        data = {'slug': 'Jack'}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 200

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, client):
        data = {'friends': [9999999999]}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession, client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()
        
        data = {'friends': [e.id]}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert "got instead entity" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_non_unique_value(self, dbsession, client):
        data = {'nickname': 'jane'}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 409
        assert 'Got non-unique value' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession, client):
        dbsession.execute(update(Entity).where(Entity.slug == 'Jane').values(deleted=True))
        dbsession.commit()

        data = {'nickname': 'jane'}
        response = client.put('/dynamic/person/Jack', json=data)
        assert response.status_code == 200
        
        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'
        
        changes = dbsession.execute(select(Change)).scalars().all()
        ent_updates = dbsession.execute(select(EntityUpdate)).scalars().all()
        val_updates = dbsession.execute(select(ValueUpdate)).scalars().all()
        assert len(changes) == 1
        assert len(ent_updates) == 1
        assert len(val_updates) == 1


class TestRouteDeleteEntity:
    @pytest.mark.parametrize('entity', [1, 'Jack'])
    def test_delete_without_review(self, dbsession, client, entity):
        response = client.delete(f'/dynamic/person/{entity}')
        assert response.json() == {'id': 1, 'slug': 'Jack', 'name': 'Jack', 'deleted': True}

        asserts_after_applying_entity_delete_request(db=dbsession, comment='Autosubmit')
        asserts_after_entity_delete(db=dbsession)

    @pytest.mark.parametrize('entity', [1234567, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, client, entity):
        response = client.delete(f'/dynamic/person/{entity}')
        assert response.status_code == 404

    @pytest.mark.parametrize('entity', [1, 'Jack'])
    def test_raise_on_already_deleted(self, dbsession, client, entity):
        dbsession.execute(update(Entity).where(Entity.id == 1).values(deleted=True))
        dbsession.commit()
        response = client.delete(f'/dynamic/person/{entity}')
        assert response.status_code == 404