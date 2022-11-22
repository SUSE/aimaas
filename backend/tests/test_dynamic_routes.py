from datetime import datetime, timezone, timedelta

import pytest

from ..models import *
from ..dynamic_routes import *
from .. import load_schemas

from .mixins import DefaultMixin


class TestRouteBasics:
    def test_load_schema_data(self, dbsession, client):
        schemas = load_schemas(db=dbsession)
        assert {s.name for s in schemas} == {'Person', 'UnPerson'}

    def test_routes_were_generated(self, dbsession, client):
        routes = [
            '/entity/person/{id_or_slug}',
            '/entity/person',
            '/entity/unperson/{id_or_slug}',
            '/entity/unperson',
            '/attributes',
            '/attributes/{attr_id}',
            '/schema/{id_or_slug}',
            '/schema/{id_or_slug}',
            '/schema'
        ]
        assert all([i in [route.path for route in client.app.routes] for i in routes])


class TestRouteCreateEntity(DefaultMixin):
    def test_create_without_review(self, dbsession, authorized_client):
        p1 = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 200
        json = response.json()
        mike_id = json.pop('id')
        assert json == {'slug': 'Mike', 'name': 'Mike', 'deleted': False}

        born = datetime(1990, 6, 30, tzinfo=timezone.utc)
        tz_born = datetime(1983, 10, 31, tzinfo=timezone(timedelta(hours=2)))
        p2 = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': [mike_id, self.get_default_entity(dbsession).id],
            'born': str(born),
        }
        response = authorized_client.post(f'/entity/person', json=p2)
        assert response.status_code == 200
        json = response.json()
        john_id = json.pop('id')
        assert json == {'slug': 'John', 'name': 'John', 'deleted': False}

        p3 = {
            'name': 'Pumpkin Jack',
            'slug': 'pumpkin-jack',
            'nickname': 'pumpkin',
            'age': 38,
            'friends': [mike_id, john_id],
            'born': str(tz_born)
        }
        response = authorized_client.post(f'/entity/person', json=p3)
        assert response.status_code == 200
        json = response.json()
        del json['id']
        assert json == {'slug': 'pumpkin-jack', 'name': 'Pumpkin Jack', 'deleted': False}

    def test_raise_on_non_unique_slug(self, dbsession, authorized_client):
        p1 = {
            'name': 'name',
            'slug': 'Jack',
            'nickname': 'test',
            'age': 10,
            'friends': []
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']

    def test_no_raise_on_same_slug_in_different_schemas(self, dbsession, authorized_client):
        data = {'slug': 'Jack', 'name': 'name'}
        response = authorized_client.post(f'/entity/unperson', json=data)
        assert response.status_code == 202  # schema is reviewable

    def test_raise_on_non_unique_field(self, dbsession, authorized_client):
        p1 = {
            'name': 'name',
            'slug': 'Jake',
            'nickname': 'jack',  # <-- already exists in db
            'age': 10,
            'friends': []
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 409
        assert 'Got non-unique value for field' in response.json()['detail']

    def test_no_raise_on_non_unique_value_if_it_is_deleted(self, dbsession, authorized_client):
        jacks = dbsession.execute(select(ValueStr).where(ValueStr.value == 'jack')).scalars().all()
        assert len(jacks) == 1

        jack = self.get_default_entity(dbsession)
        jack.deleted = True
        dbsession.commit()
        p1 = {
            'name': 'name',
            'slug': 'Jackie',
            'nickname': 'jack',  # <-- already exists in db, but for deleted entity
            'age': 10,
            'friends': []
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 200

        entity = dbsession.execute(select(Entity).where(Entity.slug == 'Jackie')).scalar()
        assert entity is not None

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, authorized_client):
        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [99999999]
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_is_deleted(self, dbsession, authorized_client):
        jack = self.get_default_entity(dbsession)
        jack.deleted = True
        dbsession.commit()
        p1 = {
            'name': 'name',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [jack.id]
        }
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_from_wrong_schema(self, dbsession, authorized_client):
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
        response = authorized_client.post(f'/entity/person', json=p1)
        assert response.status_code == 422
        assert 'got instead entity' in response.json()['detail']


class TestRouteGetEntity(DefaultMixin):
    def test_get_entity(self, dbsession, client):
        entity = self.get_default_entity(dbsession)
        data = {
            'id': entity.id,
            'slug': 'Jack',
            'name': 'Jack',
            'deleted': False,
            'age': 10,
            'friends': [],
            'born': None,
            'nickname': 'jack',
            'fav_color': ['blue', 'red']
        }
        response = client.get(f'/entity/person/{entity.id}')
        assert response.status_code == 200
        assert response.json() == data

        response = client.get(f'/entity/person/Jack')
        assert response.status_code == 200
        assert response.json() == data

    def test_raise_on_entity_doesnt_exist(self, dbsession, client):
        response = client.get('/entity/person/99999999')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_entity_doesnt_belong_to_schema(self, dbsession, client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([e, s])
        dbsession.commit()

        response = client.get(f'/entity/person/{e.id}')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']


class TestRouteGetEntities(DefaultMixin):
    def test_get_entities(self, dbsession, client):
        data = [
            {'age': 10, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'},
            {'age': 12, 'deleted': False, 'slug': 'Jane', 'name': 'Jane'}
        ]
        response = client.get(f'/entity/person/')
        assert response.status_code == 200
        assert [self.strip_ids(j) for j in response.json()['items']] == data

    def test_get_deleted_only(self, dbsession, client):
        jane = self.get_default_entities(dbsession)["Jane"]
        jane.deleted = True
        dbsession.commit()

        data = [{'age': 12, 'id': jane.id, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}]
        response = client.get(f'/entity/person?deleted_only=True')
        assert response.status_code == 200
        assert response.json()['items'] == data

    def test_get_all(self, dbsession, client):
        entities = self.get_default_entities(dbsession)
        jane = entities["Jane"]
        jane.deleted = True
        dbsession.commit()

        data = [
            {'age': 10, 'id': entities["Jack"].id, 'deleted': False, 'slug': 'Jack', 'name': 'Jack'},
            {'age': 12, 'id': jane.id, 'deleted': True, 'slug': 'Jane', 'name': 'Jane'}
        ]
        response = client.get(f'/entity/person?all=True')
        assert response.status_code == 200
        assert response.json()["items"] == data

        response = client.get(f'/entity/person?all=True&deleted_only=True')
        assert response.status_code == 200
        assert response.json()["items"] == data

    def test_get_all_fields(self, dbsession, client):
        entities = self.get_default_entities(dbsession)
        data = [
            {
                'age': 10,
                'born': None,
                'friends': [],
                'nickname': 'jack',
                'id': entities["Jack"].id,
                'deleted': False,
                'slug': 'Jack',
                'name': 'Jack',
                'fav_color': ['blue', 'red']
            },
            {
                'age': 12,
                'born': None,
                'friends': [entities["Jack"].id],
                'nickname': 'jane',
                'id': entities["Jane"].id,
                'deleted': False,
                'slug': 'Jane',
                'name': 'Jane',
                'fav_color': ['black', 'red']
             }
        ]
        response = client.get(f'/entity/person?all_fields=True')
        assert response.status_code == 200
        assert response.json()["items"] == data

    @pytest.mark.parametrize(['q', 'slugs'], [
        ('size=1',        {'Jack'}),
        ('size=1&page=2', {'Jane'}),
        ('page=10',       set())
    ])
    def test_pagination(self, dbsession, client, q, slugs):
        response = client.get('/entity/person?' + q)
        data = response.json()
        assert response.status_code == 200
        assert data["total"] == 2
        assert {i["slug"] for i in data["items"]} == slugs

    @pytest.mark.parametrize(['q', 'slugs'], [
        ('age=10',               {'Jack'}),
        ('age.lt=10',            set()),
        ('age.eq=10',            {'Jack'}),
        ('age.gt=10',            {'Jane'}),
        ('age.le=10',            {'Jack'}),
        ('age.ne=10',            {'Jane'}),
        ('age.ge=10',            {'Jack', 'Jane'}),
        ('name=Jane',            {'Jane'}),
        ('nickname=jane',        {'Jane'}),
        ('nickname.ne=jack',     {'Jane'}),
        ('nickname.regexp=^ja',  {'Jack', 'Jane'}),
        ('nickname.contains=ne', {'Jane'}),
        ('fav_color.eq=black',   {'Jane'}),
        ('fav_color.ne=black',   {'Jack', 'Jane'})  # still returns both even though Jane has black fav_color, but also has red
    ])
    def test_get_with_filter(self, dbsession, client, q, slugs):
        items = client.get(f'/entity/person?{q}').json()["items"]
        assert {i["slug"] for i in items} == slugs

    def test_get_with_multiple_filters_for_same_attr(self, dbsession, client):
        response = client.get('/entity/person?age.gt=9&age.ne=10')
        assert {i["slug"] for i in response.json()['items']} == {'Jane'}

        response = client.get('/entity/person?age.gt=9&age.ne=10&age.lt=12')
        assert response.json()['items'] == []

    @pytest.mark.parametrize(['q', 'slugs'], [
        ('age.gt=9&name.ne=Jack',               {'Jane'}),
        ('name=Jack&name.ne=Jack',              set()),
        ('nickname.ne=jane&name.ne=Jack',       set()),
        ('age.gt=9&age.ne=10&nickname.ne=jane', set())
    ])
    def test_get_with_multiple_filters(self, dbsession, client, q, slugs):
        response = client.get(f'/entity/person?{q}')
        assert {i["slug"] for i in response.json()['items']} == slugs

    def test_get_with_filters_and_offset_limit(self, dbsession, client):
        response = client.get('/entity/person?age.gt=0&age.lt=20&size=1')
        assert {i["slug"] for i in response.json()['items']} == {'Jack'}

        response = client.get('/entity/person?age.gt=0&age.lt=20&size=1&page=2')
        assert {i["slug"] for i in response.json()['items']} == {'Jane'}

        response = client.get('/entity/person?age.gt=0&age.lt=20&page=2')
        assert response.json()['items'] == []

    @pytest.mark.parametrize(['q', 'slugs'], [
        ('age.gt=0&age.lt=20',                            {'Jane'}),
        ('page=2&age.gt=0&age.lt=20',                     set()),
        ('all=True&age.gt=0&age.lt=20',                   {'Jack', 'Jane'}),
        ('deleted_only=True&age.gt=0&age.lt=20',          {'Jack'}),
        ('deleted_only=true&page=2&age.gt=0&age.lt=20',   set()),
    ])
    def test_get_with_filters_and_deleted(self, dbsession, client, q, slugs):
        jack = dbsession.scalars(select(Entity).where(Entity.slug == 'Jack')).one()
        jack.deleted = True
        dbsession.commit()
        response = client.get(f'/entity/person?{q}')
        assert {i["slug"] for i in response.json()['items']} == slugs

    def test_ignore_invalid_filter(self, dbsession, client):
        for query in ('age.gt=0&age.lt=20&qwe.rty=123', 'age.qwe=1234',
                      'age.gt=0&age.lt=20&friends.lt=1234'):
            response = client.get('/entity/person?' + query)
            assert {i["slug"] for i in response.json()['items']} == {'Jack', 'Jane'}

    def test_ignore_filters_for_fk(self, dbsession, client):
        response = client.get('/entity/person?friends=1')
        assert {i["slug"] for i in response.json()['items']} == {'Jack', 'Jane'}

    @pytest.mark.parametrize(['q', 'slugs'], [
        ('name=Jack', {'Jack'}),
        ('name=jack', set()),
        ('name.starts=Ja', {'Jack', 'Jane'}),
        ('name.starts=ja', {'Jack', 'Jane'}),
        ('name.regexp=^Jac', {'Jack'}),
        ('name.regexp=^jac', {'Jack'}),
        ('name.ieq=Jack', {'Jack'}),
        ('name.ieq=jack', {'Jack'}),
        ('nickname=Jack', set()),
        ('nickname=jack', {'Jack'}),
        ('nickname.starts=Ja', {'Jack', 'Jane'}),
        ('nickname.starts=ja', {'Jack', 'Jane'}),
        ('nickname.regexp=^Jac', {'Jack'}),
        ('nickname.regexp=^jac', {'Jack'}),
        ('nickname.ieq=Jack', {'Jack'}),
        ('nickname.ieq=jack', {'Jack'})
    ])
    def test_get_with_caseinsensitive_filter(self, dbsession, client, q, slugs):
        response = client.get(f'/entity/person?{q}')
        assert {i["slug"] for i in response.json()['items']} == slugs


class TestRouteUpdateEntity(DefaultMixin):
    def test_update(self, dbsession, authorized_client):
        entity = self.get_default_entity(dbsession)
        data = {
            'name': 'test',
            'slug': 'test',
            'nickname': None,
            'born': '2021-10-20T13:52:17+03',
            'friends': [e.id for e in self.get_default_entities(dbsession).values()],
        }
        response = authorized_client.put(f'entity/person/{entity.id}', json=data)
        assert response.status_code == 200
        assert response.json() == {'id': entity.id, 'slug': 'test', 'name': 'test', 'deleted': False}

        born_utc = datetime(2021, 10, 20, 10, 52, 17, tzinfo=timezone.utc)

        data = {
            'slug': 'test2',
            'nickname': 'test'
        }
        response = authorized_client.put('/entity/person/Jane', json=data)
        entity = self.get_default_entities(dbsession)["test2"]
        assert response.status_code == 200
        assert response.json() == {'id': entity.id, 'slug': 'test2', 'name': 'Jane', 'deleted': False}

    def test_raise_on_entity_doesnt_exist(self, dbsession, authorized_client):
        response = authorized_client.put('/entity/person/99999999999', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

        response = authorized_client.put('/entity/person/qwertyuiop', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()
        response = authorized_client.put('/entity/person/test', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_schema_is_deleted(self, dbsession, authorized_client):
        entity = self.get_default_entity(dbsession)
        entity.deleted = True
        dbsession.commit()
        response = authorized_client.put(f'/entity/person/{entity.id}', json={})
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_entity_already_exists(self, dbsession, authorized_client):
        data = {'slug': 'Jane'}
        entity = self.get_default_entity(dbsession)
        response = authorized_client.put(f'/entity/person/{entity.id}', json=data)
        assert response.status_code == 409
        assert 'already exists in this schema' in response.json()['detail']

    def test_no_raise_on_changing_to_same_slug(self, dbsession, authorized_client):
        data = {'slug': 'Jack'}
        entity = self.get_default_entity(dbsession)
        response = authorized_client.put(f'/entity/person/{entity.id}', json=data)
        assert response.status_code == 208

    def test_raise_on_invalid_slug(self, dbsession, authorized_client):
        p1 = {
            'slug': '-Jake-',
        }
        response = authorized_client.put('/entity/person/Jack', json=p1)
        assert response.status_code == 422
        assert 'is invalid value for slug field' in response.json()['detail'][0]['msg']

    def test_raise_on_deleting_required_value(self, dbsession, authorized_client):
        data = {'age': None}
        response = authorized_client.put('entity/person/Jack', json=data)
        assert response.status_code == 422
        assert 'Missing required field' in response.json()['detail']

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession, authorized_client):
        data = {'age': [1, 2, 3, 4, 5]}
        response = authorized_client.put('entity/person/Jack', json=data)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_fk_entity_doesnt_exist(self, dbsession, authorized_client):
        data = {'friends': [9999999999]}
        response = authorized_client.put('/entity/person/Jack', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_fk_entity_is_from_wrong_schema(self, dbsession, authorized_client):
        s = Schema(name='test', slug='test')
        e = Entity(slug='test', schema=s, name='test')
        dbsession.add_all([s, e])
        dbsession.commit()

        data = {'friends': [e.id]}
        response = authorized_client.put('/entity/person/Jack', json=data)
        assert response.status_code == 422
        assert "got instead entity" in response.json()['detail']

    def test_raise_on_non_unique_value(self, dbsession, authorized_client):
        data = {'nickname': 'jane'}
        response = authorized_client.put('/entity/person/Jack', json=data)
        assert response.status_code == 409
        assert 'Got non-unique value' in response.json()['detail']

    def test_no_raise_on_non_unique_if_existing_is_deleted(self, dbsession, authorized_client):
        jane = self.get_default_entities(dbsession)["Jane"]
        jane.deleted = True
        dbsession.commit()

        data = {'nickname': 'jane'}
        response = authorized_client.put('/entity/person/Jack', json=data)
        assert response.status_code == 200

        e = dbsession.execute(select(Entity).where(Entity.slug == 'Jack')).scalar()
        assert e.get('nickname', dbsession).value == 'jane'

    def test_raise_on_value_out_of_range(self, dbsession, authorized_client):
        response = authorized_client.put('/entity/person/Jack', json={"age": 2147483648})
        assert response.status_code == 422

    def test_no_raise_on_missing_data(self, dbsession, authorized_client):
        response = authorized_client.put('/entity/person/Jack', json={})
        assert response.status_code == 208


class TestRouteDeleteEntity(DefaultMixin):
    def test_delete(self, dbsession, authorized_client):
        entity = self.get_default_entity(dbsession)
        response = authorized_client.delete(f'/entity/person/{entity.slug}')
        assert response.status_code == 200
        assert response.json() == {'id': entity.id, 'slug': 'Jack', 'name': 'Jack', 'deleted': True}

        dbsession.refresh(entity)
        assert entity.deleted

    @pytest.mark.parametrize('entity', [1234567, 'qwertyu'])
    def test_raise_on_entity_doesnt_exist(self, dbsession, authorized_client, entity):
        response = authorized_client.delete(f'/entity/person/{entity}')
        assert response.status_code == 404

    def test_raise_on_already_deleted(self, dbsession, authorized_client):
        entity = self.get_default_entity(dbsession)
        entity.deleted = True
        dbsession.commit()
        response = authorized_client.delete(f'/entity/person/{entity.id}')
        assert response.status_code == 404
