from datetime import timedelta, timezone
from typing import List

from sqlalchemy import update
import pytest
from fastapi.testclient import TestClient
from dateutil import parser

from ..models import *
from ..schemas import *
from .test_crud_schema import (
    asserts_after_schema_create,
    asserts_after_schema_update,
    asserts_after_schema_delete
)
from .test_traceability_schema import (
    asserts_after_applying_schema_create_request,
    asserts_after_submitting_schema_create_request,
    asserts_after_applying_schema_update_request,
    asserts_after_submitting_schema_update_request,
    asserts_after_applying_schema_delete_request,
    asserts_after_submitting_schema_delete_request,
    make_schema_change_objects,
    make_schema_update_request
)
from .test_traceability_entity import (
    make_entity_change_objects,
    make_entity_update_request,
    make_entity_delete_request
)

class TestRouteAttributes:
    def test_get_attributes(self, dbsession: Session, client: TestClient):
        attrs = [
            {'id': 1, 'name': 'age', 'type': 'FLOAT'},
            {'id': 2, 'name': 'age', 'type': 'INT'},
            {'id': 3, 'name': 'age', 'type': 'STR'},
            {'id': 4, 'name': 'born', 'type': 'DT'},
            {'id': 5, 'name': 'friends', 'type': 'FK'},
            {'id': 6, 'name': 'address', 'type': 'FK'},
            {'id': 7, 'name': 'nickname', 'type': 'STR'},
            {'id': 8, 'name': 'fav_color', 'type': 'STR'}
        ]
        response = client.get('/attributes')
        assert response.json() == attrs

    def test_get_attribute(self, dbsession: Session, client: TestClient):
        response = client.get('/attributes/1')
        assert response.json() == {'id': 1, 'name': 'age', 'type': 'FLOAT'}

    def test_raise_on_attribute_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/attributes/123456789')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']


class TestRouteSchemasGet:
    def test_get_schemas(self, dbsession: Session, client: TestClient):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}]

    def test_get_all(self, dbsession: Session, client: TestClient):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas?all=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}, {'id': 2, 'name': 'Test', 'slug': 'test'}]

        response = client.get('/schemas?all=True&deleted_only=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 1, 'name': 'Person', 'slug': 'person'}, {'id': 2, 'name': 'Test', 'slug': 'test'}]

    def test_get_deleted_only(self, dbsession: Session, client: TestClient):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schemas?deleted_only=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 2, 'name': 'Test', 'slug': 'test'}]

    def test_raise_on_schema_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/schemas/123456789')
        assert response.status_code == 404

    def test_get_schema(self, dbsession: Session, client: TestClient):
        attrs = [
            {
                'bind_to_schema': None,
                'description': 'Age of this person',
                'key': True,
                'list': False,
                'name': 'age',
                'required': True,
                'type': 'INT',
                'unique': False
            },
            {
                'bind_to_schema': None,
                'description': None,
                'key': False,
                'list': False,
                'name': 'born',
                'required': False,
                'type': 'DT',
                'unique': False
            },
            {
                'bind_to_schema': 1,
                'description': None,
                'key': False,
                'list': True,
                'name': 'friends',
                'required': True,
                'type': 'FK',
                'unique': False
            },
            {
                'bind_to_schema': None,
                'description': None,
                'key': False,
                'list': False,
                'name': 'nickname',
                'required': False,
                'type': 'STR',
                'unique': True
            },
            {
                'bind_to_schema': None,
                'description': None,
                'key': False,
                'list': True,
                'name': 'fav_color',
                'required': False,
                'type': 'STR',
                'unique': False
            }
        ]       
        schema = {
            'deleted': False,
            'id': 1,
            'name': 'Person',
            'slug': 'person',
            'reviewable': False
        }
        attrs = sorted(attrs, key=lambda x: x['name'])

        response = client.get('/schemas/1')
        json = response.json()
        assert sorted(json['attributes'], key=lambda x: x['name']) == attrs
        del json['attributes']
        assert json == schema

        response = client.get('/schemas/person')
        json = response.json()
        assert sorted(json['attributes'], key=lambda x: x['name']) == attrs
        del json['attributes']
        assert json == schema
    

class TestRouteSchemaCreate:
    def assert_no_change_requests_appeared(self, db: Session):
        assert db.execute(select(Change)).scalar() is None
        assert db.execute(select(SchemaCreate)).scalar() is None
        assert db.execute(select(AttributeCreate)).scalar() is None

    def test_create_without_review(self, dbsession: Session, client):
        data = {
            'name': 'Car',
            'slug': 'car',
            'attributes': [
                {
                    'name': 'color',
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Color of this car'
                },
                {
                    'name': 'max_speed',
                    'type': 'INT',
                    'required': True,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'name': 'release_year',
                    'type': 'DT',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'name': 'owner',
                    'type': 'FK',
                    'required': True,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 1
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 200
        json = response.json()
        del json['id']
        assert json == {'name': 'Car', 'slug': 'car'}
        assert '/dynamic/car' in [i.path for i in client.app.routes]
        asserts_after_applying_schema_create_request(dbsession, change_id=1, comment='Autosubmit')
        asserts_after_schema_create(dbsession)

    def test_raise_on_duplicate_name_or_slug(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Person',
            'slug': 'test',
            'attributes': []
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

        data = {
            'name': 'Test',
            'slug': 'person',
            'attributes': []
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_empty_schema_when_binding(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'owner',
                    'type': 'FK',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 422
        assert "You must bind attribute" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'owner',
                    'type': 'FK',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 123456789
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_passed_deleted_schema_for_binding(self, dbsession: Session, client: TestClient):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'owner',
                    'type': 'FK',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 1
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'test1',
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'name': 'test1',
                    'type': 'INT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.post('/schemas', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)


class TestRouteSchemaUpdate:
    def assert_no_change_requests_appeared(self, db: Session):
        assert db.execute(select(Change)).scalar() is None
        assert db.execute(select(SchemaUpdate)).scalar() is None
        assert db.execute(select(AttributeCreate)).scalar() is None
        assert db.execute(select(AttributeUpdate)).scalar() is None
        assert db.execute(select(AttributeDelete)).scalar() is None

    def test_update_without_review(self, dbsession: Session, client: TestClient):
        data = {
            'slug': 'test',
            'reviewable': True,
            'update_attributes': [
                {
                    'name': 'age',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Age of this person'
                }
            ],
            'add_attributes': [
                {
                    'name': 'address',
                    'type': 'FK',
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True,
                    'bind_to_schema': -1
                }
            ]
        } 
        result = {'name': 'Person', 'slug': 'test'}
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 200
        json = response.json()
        del json['id']
        assert json == result

        routes = [i.path for i in client.app.routes]
        assert '/dynamic/test' in routes
        assert '/dynamic/person' not in routes

        asserts_after_applying_schema_update_request(db=dbsession, comment='Autosubmit')
        asserts_after_schema_update(db=dbsession)


    def test_raise_on_existing_slug_or_name(self, dbsession: Session, client: TestClient):
        new_sch = Schema(name='Test', slug='test')
        dbsession.add(new_sch)
        dbsession.commit()
        
        data = {
            'name': 'Test',
            'slug': 'person'
        }
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

        data = {
            'name': 'Person',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': []
        }
        response = client.put('/schemas/person', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_attr_not_defined_on_schema(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'name': 'address',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 404
        assert "is not defined on schema" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_convert_list_to_single(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [
                {
                    'name': 'friends',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "is listed, can't make unlisted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': 'address',
                    'type': 'FK',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': 123456789
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_schema_not_passed_when_binding(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'add_attributes': [
                {
                    'name': 'address',
                    'type': 'FK',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 422
        assert "You must bind attribute" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': 'address',
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                },
                {
                    'name': 'address',
                    'type': 'INT',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']
        self.assert_no_change_requests_appeared(dbsession)


class TestRouteSchemaDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_delete(self, dbsession: Session, client: TestClient, id_or_slug):
        response = client.delete(f'/schemas/{id_or_slug}')
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'name': 'Person', 'slug': 'person', 'deleted': True, 'reviewable': False}

        asserts_after_applying_schema_delete_request(db=dbsession, comment='Autosubmit')
        asserts_after_schema_delete(db=dbsession)

    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_raise_on_already_deleted(self, dbsession: Session, client: TestClient, id_or_slug):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        response = client.delete(f'/schemas/{id_or_slug}')
        assert response.status_code == 404


class TestRouteGetEntityChanges:
    def test_get_recent_changes(self, dbsession: Session, client: TestClient):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow()
        make_entity_change_objects(db=dbsession, user=user, time=now)

        response = client.get('/changes/entity/person/Jack?count=1')
        changes = response.json()
        assert parser.parse(changes[0]['created_at']).replace(tzinfo=timezone.utc) == (now + timedelta(hours=9)).replace(tzinfo=timezone.utc)
        
        response = client.get('/changes/entity/person/Jack')
        changes = response.json()
        for change, i in zip(changes, reversed(range(5, 10))):
            assert parser.parse(change['created_at']).replace(tzinfo=timezone.utc) == (now + timedelta(hours=i)).replace(tzinfo=timezone.utc)

    def test_get_update_details(self, dbsession: Session, client: TestClient):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        make_entity_update_request(db=dbsession, user=user, time=now)

        response = client.get('/changes/entity/person/Jack/1')
        change = response.json()
        assert parser.parse(change['created_at']) == now
        assert change['created_by'] == user.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change['entity']['name'] == 'Jack'
        assert change['entity']['slug'] == 'Jack'
        assert change['entity']['schema'] == 'person'
        assert len(change['changes']) == 3
        name = change['changes']['name']
        age = change['changes']['age']
        fav_color = change['changes']['fav_color']
        assert name['new'] == 'Jackson' and name['old'] == name['current'] == 'Jack'
        assert age['new'] == '42' and age['old'] == age['current'] == '10'
        assert fav_color['new'] == ['violet', 'cyan'] and fav_color['old'] == fav_color['current'] == None
    # TODO
    # test for create details

    def test_get_delete_details(self, dbsession: Session, client: TestClient):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        make_entity_delete_request(db=dbsession, user=user, time=now)

        response = client.get('/changes/entity/person/Jack/1')
        change = response.json()
        assert parser.parse(change['created_at']) == now
        assert change['created_by'] == user.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change['entity']['name'] == 'Jack'
        assert change['entity']['slug'] == 'Jack'
        assert change['entity']['schema'] == 'person'
        assert len(change['changes']) == 1
        deleted = change['changes']['deleted']
        assert deleted['new'] == 'True' and deleted['old'] == deleted['current'] == 'False'

    def test_raise_on_change_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/entity/person/Jack/12345678')
        assert response.status_code == 404

    def test_raise_on_schema_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/entity/1234567890/Jack/1')
        assert response.status_code == 404

        response = client.get('/changes/entity/1234567890/Jack')
        assert response.status_code == 404

    def test_raise_on_entity_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/entity/person/123456789/1')
        assert response.status_code == 404

        response = client.get('/changes/entity/person/123456789')
        assert response.status_code == 404


class TestRouteGetSchemaChanges:
    def test_get_recent_changes(self, dbsession: Session, client: TestClient):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow()
        make_schema_change_objects(db=dbsession, user=user, time=now)

        response = client.get('/changes/schema/person?count=1')
        changes = response.json()
        assert parser.parse(changes[0]['created_at']).replace(tzinfo=timezone.utc) == (now + timedelta(hours=9)).replace(tzinfo=timezone.utc)
        
        response = client.get('/changes/schema/person')
        changes = response.json()
        for change, i in zip(changes, reversed(range(5, 10))):
            assert parser.parse(change['created_at']).replace(tzinfo=timezone.utc) == (now + timedelta(hours=i)).replace(tzinfo=timezone.utc)
    
    def test_get_update_details(self, dbsession: Session, client: TestClient):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        make_schema_update_request(db=dbsession, user=user, time=now)

        response = client.get('/changes/schema/person/1')
        change = response.json()
        assert parser.parse(change['created_at']) == now
        assert change['created_by'] == user.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change['schema']['name'] == 'Person'
        assert change['schema']['slug'] == 'person'

        assert len(change['changes']) == 7
        assert change['changes']['name'] == change['changes']['deleted'] == None
        slug = change['changes']['slug']
        reviewable = change['changes']['reviewable']
        add = change['changes']['add']
        update = change['changes']['update']
        delete = change['changes']['delete']

        assert slug['new'] == 'test' and slug['old'] == slug['current'] == 'person'
        assert reviewable['new'] == True and reviewable['old'] == reviewable['current'] == False
        assert all(len(i) == 1 for i in [add, update, delete])

        assert AttrDefSchema(**add[0]) == AttrDefSchema(
            name='test',
            type='STR',
            required=False,
            unique=False,
            list=False,
            key=False,
        )
        assert AttrDefUpdateSchema(**update[0]) == AttrDefUpdateSchema(
            name='age',
            new_name='AGE',
            required=True,
            unique=True,
            list=True,
            key=True,
            description='AGE'
        )
        assert delete[0] == 'born'


    # # TODO
    # # test for create details

    # def test_get_delete_details(self, dbsession: Session, client: TestClient):
    #     user = dbsession.execute(select(User)).scalar()
    #     now = datetime.utcnow().replace(tzinfo=timezone.utc)
    #     make_entity_delete_request(db=dbsession, user=user, time=now)

    #     response = client.get('/changes/entity/person/Jack/1')
    #     change = response.json()
    #     assert parser.parse(change['created_at']) == now
    #     assert change['created_by'] == user.username
    #     assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
    #     assert change['status'] == 'PENDING'
    #     assert change['entity']['name'] == 'Jack'
    #     assert change['entity']['slug'] == 'Jack'
    #     assert change['entity']['schema'] == 'person'
    #     assert len(change['changes']) == 1
    #     deleted = change['changes']['deleted']
    #     assert deleted['new'] == 'True' and deleted['old'] == deleted['current'] == 'False'

    def test_raise_on_change_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/schema/person/Jack/12345678')
        assert response.status_code == 404

    def test_raise_on_schema_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/schema/1234567890/1')
        assert response.status_code == 404

        response = client.get('/changes/schema/1234567890')
        assert response.status_code == 404
