import pytest
from sqlalchemy import select, update
from fastapi.testclient import TestClient

from backend.schemas import EntityListSchema

from ..models import *
from ..dynamic_routes import *


class TestRouteGetEntities:
    @pytest.mark.parametrize('params', [
        {},
        {'limit': 10},
        {'offset': 10},
        {'all': 'true'},
        {'deleted_only': 'true'},
        {'meta': 'true'},
        {'name.ne': 'test'},
        {'order_by': 'name'},
        {'ascending': 'false'},
        {'limit': 10, 'offset': 10},
        {'limit': 10, 'offset': 10, 'all': 'true'},
        {'limit': 10, 'offset': 10, 'all': 'true', 'meta': 'true'},
        {'limit': 10, 'offset': 10, 'all': 'true', 'meta': 'true', 'name.ne': 'test'},
        {'limit': 10, 'offset': 10, 'all': 'true', 'meta': 'true', 'name.ne': 'test', 'order_by': 'name'},
        {'limit': 10, 'offset': 10, 'all': 'true', 'meta': 'true', 'name.ne': 'test', 'order_by': 'name', 'ascending': 'false'},
    ])
    def test_get_entities_with_different_params(self, mocker, params: dict, dbsession: Session, client: TestClient):
        mocker.patch('backend.crud.get_entities', return_value=EntityListSchema(total=0, entities=[]))
        response = client.get('/dynamic/person', params=params)
        assert response.status_code < 400
    

class TestRouteCreateEntity:
    def test_create_with_ok_body(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_entity_create_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_entity_create_request', return_value=dbsession.execute(select(Entity)).scalar())
        data = {
            'name': 'Mike',
            'slug': 'Mike',
            'nickname': 'mike',
            'age': 10,
            'friends': [],
        }
        response = client.post(f'/dynamic/person', json=data)
        assert response.status_code < 400


    def test_raise_on_invalid_slug(self, dbsession, client):
        p1 = {
            'slug': '-Jake-', 
            'nickname': 'jackie',
            'age': 10,
            'friends': []
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 422
        assert 'is invalid value for slug field' in response.json()['detail'][0]['msg']

    def test_raise_on_attr_doesnt_exist(self, dbsession, client):
        p = {
            'name': 'name',
            'slug': 'SomeName',
            'nickname': 'somename',
            'age': 10,
            'friends': [1],
            'nonexistent': True
        }
        response = client.post(f'/dynamic/person', json=p)
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
        response = client.post(f'/dynamic/person', json=p)
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
        response = client.post(f'/dynamic/person', json=p)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_passed_single_value_for_list_attr(self, dbsession, client):
        p = {
            'name': 'name',
            'slug': 'Some name',
            'nickname': 'somename',
            'age': 2,
            'friends': 1,
        }
        response = client.post(f'/dynamic/person', json=p)
        assert response.status_code == 422
        assert 'value is not a valid list' in response.json()['detail'][0]['msg']
        
    def test_raise_on_slug_not_provided(self, dbsession, client):
        p1 = {
            'nickname': 'mike',
            'age': 10,
            'friends': [1]
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 422
        assert 'field required' in response.json()['detail'][0]['msg']

    def test_raise_on_required_field_not_provided(self, dbsession, client):
        p1 = {
            'slug': 'Mike',
            'friends': [1]
        }
        response = client.post(f'/dynamic/person', json=p1)
        assert response.status_code == 422
        assert 'field required' in response.json()['detail'][0]['msg']


class TestRouteUpdateEntity:
    def test_update_with_ok_body(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_entity_update_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_entity_update_request', return_value=dbsession.execute(select(Entity)).scalar())
        data = {
            'name': 'test',
            'slug': 'test',
            'nickname': None,
            'born': '2021-10-20T13:52:17+03',
            'friends': [1, 2],
        }
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code < 400


    def test_raise_on_invalid_slug(self, dbsession, client):
        p1 = {
            'slug': '-Jake-', 
        }
        response = client.put(f'/dynamic/person/1', json=p1)
        assert response.status_code == 422
        assert 'is invalid value for slug field' in response.json()['detail'][0]['msg']

    def test_raise_on_deleting_required_value(self, dbsession, client):
        data = {'age': None}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert 'Missing required field' in response.json()['detail']

    def test_raise_on_attribute_not_defined_on_schema(self, dbsession, client):
        data = {'not_existing_attr': 50000}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert 'extra fields not permitted' in response.json()['detail'][0]['msg']

        data = {'address': 1234}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert 'extra fields not permitted' in response.json()['detail'][0]['msg']

    def test_raise_on_passing_list_for_not_listed_attr(self, dbsession, client):
        data = {'age': [1, 2, 3, 4, 5]}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert 'value is not a valid integer' in response.json()['detail'][0]['msg']

    def test_raise_on_passing_single_value_for_listed_attr(self, dbsession, client):
        data = {'friends': 1}
        response = client.put('/dynamic/person/1', json=data)
        assert response.status_code == 422
        assert 'value is not a valid list' in response.json()['detail'][0]['msg']
    
class TestRouteDeleteEntity:
    def test_delete_with_ok_body(self, mocker, dbsession: Session, client: TestClient):
        mocker.patch('backend.traceability.create_entity_delete_request', return_value=Change(id=1))
        mocker.patch('backend.traceability.apply_entity_delete_request', return_value=dbsession.execute(select(Entity)).scalar())

        response = client.delete(f'/dynamic/person/1')
        assert response.status_code < 400

        response = client.delete(f'/dynamic/person/Jack')
        assert response.status_code < 400