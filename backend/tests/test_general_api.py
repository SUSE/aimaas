import pytest
from pydantic import BaseModel
from fastapi.testclient import TestClient

from ..models import *


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
    @pytest.mark.parametrize('params', [
        {}, 
        {'all': 'True'}, 
        {'all': 'False'}, 
        {'deleted_only': 'True'},
        {'deleted_only': 'False'},
        {'all': 'True', 'deleted_only': 'True'}, 
        {'all': 'True', 'deleted_only': 'False'}, 
        {'all': 'False', 'deleted_only': 'True'},
    ])
    def test_get_schemas_with_different_params(self, mocker, params: dict, dbsession: Session, client: TestClient):
        mocker.patch('backend.crud.get_schemas', return_value=[])
        response = client.get('/schemas', params=params)
        assert response.status_code < 400

    
class TestRouteSchemaCreate:
    def test_body_is_ok(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_schema_create_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_schema_create_request', return_value=dbsession.execute(select(Schema)).scalar())
        mocker.patch('backend.crud.create_schema', return_value={})

        schema = {
            'name': 'Test',
            'slug': 'test',
            'reviewable': True,
            'attributes': [
                {
                    'name': 'attr1',
                    'type': 'STR',
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True
                },
                {
                    'name': 'attr2',
                    'type': 'FK',
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True,
                    'bind_to_schema': -1,
                    'description': 'attr2'
                }
            ]
        }

        response = client.post('/schemas', json=schema)
        assert response.status_code == 200


    @pytest.mark.parametrize(['symbol'], [i for i in '!@"`~#№;$%^&?:,.*()-=+/\\<>'])
    def test_raise_on_invalid_attr_name(self, dbsession: Session, client: TestClient, symbol):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': f'abc{symbol}abc',
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 422

    @pytest.mark.parametrize(['name'], [(i,) for i in ['_i', 'i_', '_i_', '__i__', '___i___', '__dict__']])
    def test_raise_on_dunder_attr(self, dbsession: Session, client: TestClient, name):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': name,
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 422

    @pytest.mark.parametrize(['attr'], [
        ('abc', ), 
        ('abc123', ), 
        ('ąbć', )  # we are not limited to letters from English alphabet
    ] + [(i, ) for i in dir(BaseModel) if not i.startswith('_') and not i.endswith('_')])
    def test_no_raise_on_valid_attr_name(self, dbsession: Session, client: TestClient, attr):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': attr,
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        }
        response = client.post('/schemas', json=data)
        assert response.status_code == 200


class TestRouteSchemaUpdate:
    def test_update_with_ok_body(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_schema_update_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_schema_update_request', return_value=dbsession.execute(select(Schema)).scalar())
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
            ],
            'remove_attributes': ['born']
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code < 400
        
        del data['remove_attributes']
        response = client.put('/schemas/1', json=data)
        assert response.status_code < 400

        del data['add_attributes']
        response = client.put('/schemas/1', json=data)
        assert response.status_code < 400

        del data['update_attributes']
        response = client.put('/schemas/1', json=data)
        assert response.status_code < 400

        del data['reviewable']
        response = client.put('/schemas/1', json=data)
        assert response.status_code < 400

    def test_raise_on_schema_doesnt_exist(self, dbsession: Session, client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'person',
            'update_attributes': [],
            'add_attributes': []
        }
        response = client.put('/schemas/12345678', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    @pytest.mark.parametrize(['symbol'], [i for i in '!@"`~#№;$%^&?:,.*()-=+/\\<>'])
    def test_raise_on_invalid_attr_name(self, dbsession: Session, client: TestClient, symbol):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': f'abc{symbol}abc',
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/1', json=data)
        assert response.status_code == 422

    @pytest.mark.parametrize(['name'], [(i,) for i in ['_i', 'i_', '_i_', '__i__', '___i___', '__dict__']])
    def test_raise_on_dunder_attr(self, dbsession: Session, client: TestClient, name):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': name,
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/person', json=data)
        assert response.status_code == 422

    @pytest.mark.parametrize(['attr'], [
        ('abc', ), 
        ('abc123', ), 
        ('ąbć', )  # we are not limited to letters from English alphabet
    ] + [(i, ) for i in dir(BaseModel) if not i.startswith('_') and not i.endswith('_')])
    def test_no_raise_on_valid_attr_name(self, dbsession: Session, client: TestClient, attr):
        data = {
            'name': 'Test',
            'slug': 'test',
            'update_attributes': [],
            'add_attributes': [
                {
                    'name': attr,
                    'type': 'STR',
                    'required':False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bind_to_schema': -1
                }
            ]
        } 
        response = client.put('/schemas/person', json=data)
        assert response.status_code == 200

class TestRouteSchemaDelete:
    def test_delete_with_ok_body(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_schema_delete_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_schema_delete_request', return_value=dbsession.execute(select(Schema)).scalar())
        response = client.delete(f'/schemas/1')
        assert response.status_code < 400

        response = client.delete(f'/schemas/person')
        assert response.status_code < 400

    @pytest.mark.parametrize('id_or_slug', [1234567, 'qwerty'])
    def test_raise_on_delete_nonexistent(self, dbsession: Session, client: TestClient, id_or_slug):
        response = client.delete(f'/schemas/{id_or_slug}')
        assert response.status_code == 404