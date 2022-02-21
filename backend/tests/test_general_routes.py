from datetime import timedelta, timezone, datetime

from fastapi.testclient import TestClient
from dateutil import parser
from sqlalchemy import update, select
from sqlalchemy.orm import Session
import pytest

from ..auth.models import User
from ..models import Schema
from ..schemas import AttrDefSchema, SchemaCreateSchema, SchemaUpdateSchema
from ..traceability.entity import create_entity_update_request, create_entity_create_request, \
    create_entity_delete_request
from ..traceability.enum import ChangeStatus
from ..traceability.models import ChangeRequest, Change
from ..traceability.schema import create_schema_create_request, create_schema_delete_request, \
    create_schema_update_request


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

        response = client.get('/schema')
        assert response.status_code == 200
        assert response.json() == [
            {'id': 1, 'name': 'Person', 'slug': 'person', 'deleted': False},
            {'id': 2, 'name': 'UnPerson', 'slug': 'unperson', 'deleted': False}
        ]

    def test_get_all(self, dbsession: Session, client: TestClient):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        expected = [
            {'id': 1, 'name': 'Person', 'slug': 'person', 'deleted': False},
            {'id': 2, 'name': 'UnPerson', 'slug': 'unperson', 'deleted': False},
            {'id': 3, 'name': 'Test', 'slug': 'test', 'deleted': True}
        ]

        response = client.get('/schema?all=True')
        assert response.status_code == 200
        assert response.json() == expected

        response = client.get('/schema?all=True&deleted_only=True')
        assert response.status_code == 200
        assert response.json() == expected

    def test_get_deleted_only(self, dbsession: Session, client: TestClient):
        test = Schema(name='Test', slug='test', deleted=True)
        dbsession.add(test)
        dbsession.commit()

        response = client.get('/schema?deleted_only=True')
        assert response.status_code == 200
        assert response.json() == [{'id': 3, 'name': 'Test', 'slug': 'test', 'deleted': True}]

    def test_get_schema(self, dbsession: Session, client: TestClient):
        attrs = [
            {
                'bound_schema_id': None,
                'description': 'Age of this person',
                'key': True,
                'list': False,
                'name': 'age',
                'required': True,
                'type': 'INT',
                'unique': False
            },
            {
                'bound_schema_id': None,
                'description': None,
                'key': False,
                'list': False,
                'name': 'born',
                'required': False,
                'type': 'DT',
                'unique': False
            },
            {
                'bound_schema_id': 1,
                'description': None,
                'key': False,
                'list': True,
                'name': 'friends',
                'required': True,
                'type': 'FK',
                'unique': False
            },
            {
                'bound_schema_id': None,
                'description': None,
                'key': False,
                'list': False,
                'name': 'nickname',
                'required': False,
                'type': 'STR',
                'unique': True
            },
            {
                'bound_schema_id': None,
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

        for id_or_slug in ('1', 'person'):
            response = client.get(f'/schema/{id_or_slug}')
            json = response.json()
            assert {a["name"] for a in json['attributes']} == {a["name"] for a in attrs}
            del json['attributes']
            assert json == schema

    def test_raise_on_schema_doesnt_exist(self, dbsession, client):
        response = client.get('/schema/12345678')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

        response = client.get('/schema/qwertyui')
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']


class TestRouteSchemaCreate:
    def test_create(self, dbsession: Session, authorized_client: TestClient):
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
                    'bound_schema_id': 1
                }
            ]
        }
        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 200
        json = response.json()
        del json['id']
        assert json == {'name': 'Car', 'slug': 'car', 'deleted': False}
        assert '/entity/car' in [i.path for i in authorized_client.app.routes]

        response = authorized_client.get('/entity/car')
        assert response.status_code == 200

    def test_raise_on_duplicate_name_or_slug(self, dbsession, authorized_client):
        data = {
            'name': 'Person',
            'slug': 'test',
            'attributes': []
        }
        response = authorized_client.post('/schema', json=data)
        assert dbsession.query(Schema).filter(Schema.name == "Person").count() == 1
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

        data = {
            'name': 'Test',
            'slug': 'person',
            'attributes': []
        }
        response = authorized_client.post('/schema', json=data)
        assert dbsession.query(Schema).filter(Schema.slug == "person").count() == 1
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_raise_on_empty_schema_when_binding(self, dbsession: Session, authorized_client: TestClient):
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
                }
            ]
        } 
        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 422
        assert "Attribute type FK must be bound to a specific schema" in response.text

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession: Session, authorized_client: TestClient):
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
                    'bound_schema_id': 123456789
                }
            ]
        } 
        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_passed_deleted_schema_for_binding(self, dbsession: Session, authorized_client: TestClient):
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
                    'bound_schema_id': 1
                }
            ]
        } 
        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [
                {
                    'name': 'test1',
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                },
                {
                    'name': 'test1',
                    'type': 'INT',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 409
        assert dbsession.query(Schema).filter(Schema.slug == "test").count() == 0
        assert "Found multiple occurrences of attribute" in response.json()['detail']

    def test_raise_on_invalid_attribute_name(self, dbsession: Session,
                                             authorized_client: TestClient):
        data = {
            "name": "Test",
            "slug": "test",
            "attributes": [{
                "name": '403',
                "type": "INT",
                "required": True,
                "unique": False,
                "list": False,
                "key": True,
                "description": 'Age of this person'
            }]
        }

        response = authorized_client.post('/schema', json=data)
        assert response.status_code == 422

        assert dbsession.query(Schema).filter(Schema.slug == "test").count() == 0


class TestRouteSchemaUpdate:
    default_attributes = [
        {
            "id": 1,
            "name": 'age',
            "type": "INT",
            "required": True,
            "unique": False,
            "list": False,
            "key": True,
            "description": 'Age of this person'
        },
        {
            "id": 2,
            "name": 'born',
            "type": 'DT',
            "required": False,
            "unique": False,
            "list": False,
            "key": False
        },
        {
            "id": 3,
            "name": 'friends',
            "type": 'FK',
            "required": True,
            "unique": False,
            "list": True,
            "key": False,
            "bound_schema_id": -1
        },
        {
            "id": 4,
            "name": 'nickname',
            "type": 'STR',
            "required": False,
            "unique": True,
            "list": False,
            "key": False
        },
        {
            "id": 5,
            "name": 'fav_color',
            "type": 'STR',
            "required": False,
            "unique": False,
            "list": True,
            "key": False
        }
    ]

    def test_update(self, dbsession: Session, authorized_client: TestClient):
        attributes = [a for a in self.default_attributes if a["id"] != 1]
        data = {
            'slug': 'test',
            'reviewable': True,
            'attributes': attributes + [
                {
                    'id': 1,
                    'name': 'age',
                    'type': 'INT',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'description': 'Age of this person'
                },
                {
                    'name': 'address',
                    'type': 'FK',
                    'required': True,
                    'unique': True,
                    'list': True,
                    'key': True,
                    'bound_schema_id': -1
                }
            ],
            'delete_attributes': ['friends']
        }
        result = {'name': 'Person', 'slug': 'test', 'deleted': False}
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 200
        json = response.json()
        del json['id']
        assert json == result

        routes = [i.path for i in authorized_client.app.routes]
        assert '/entity/test' in routes
        assert '/entity/person' not in routes

    def test_raise_on_schema_doesnt_exist(self, dbsession, authorized_client):
        data = {
            'name': 'Test',
            'slug': 'person',
            'attributes': []
        }
        response = authorized_client.put('/schema/12345678', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_existing_slug_or_name(self, dbsession: Session, authorized_client: TestClient):
        new_sch = Schema(name='Test', slug='test')
        dbsession.add(new_sch)
        dbsession.commit()
        
        data = {
            'name': 'Test',
            'slug': 'person'
        }
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

        data = {
            'name': 'Person',
            'slug': 'test',
            'attributes': []
        }
        response = authorized_client.put('/schema/person', json=data)
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_raise_on_attr_not_defined_on_schema(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': self.default_attributes + [
                {
                    'id': 56789,
                    'name': 'address',
                    'type': 'STR',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ]
        } 
        response = authorized_client.put('/schema/1', json=data)
        print("===DEBUG===", response.json())
        assert response.status_code == 404
        assert "is not defined on schema" in response.json()['detail']

    def test_raise_on_convert_list_to_single(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': [a for a in self.default_attributes if a["id"] != 3] + [
                {
                    'id': 3,
                    'name': 'friends',
                    'type': 'STR',
                    'required': True,
                    'unique': True,
                    'list': False,
                    'key': True
                }
            ]
        } 
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 409
        assert "is listed, can't make unlisted" in response.text

    def test_raise_on_nonexistent_schema_when_binding(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': self.default_attributes + [
                {
                    'name': 'address',
                    'type': 'FK',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bound_schema_id': 123456789
                }
            ]
        } 
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 404
        assert "doesn't exist or was deleted" in response.json()['detail']

    def test_raise_on_schema_not_passed_when_binding(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': self.default_attributes + [
                {
                    'name': 'address',
                    'type': 'FK',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                }
            ]
        } 
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 422
        assert "Attribute type FK must be bound to a specific schema" in response.text

    def test_raise_on_multiple_attrs_with_same_name(self, dbsession: Session, authorized_client: TestClient):
        data = {
            'name': 'Test',
            'slug': 'test',
            'attributes': self.default_attributes + [
                {
                    'name': 'address',
                    'type': 'STR',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bound_schema_id': -1
                },
                {
                    'name': 'address',
                    'type': 'INT',
                    'required': False,
                    'unique': False,
                    'list': False,
                    'key': False,
                    'bound_schema_id': -1
                }
            ]
        } 
        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 409
        assert "Found multiple occurrences of attribute" in response.json()['detail']

    def test_raise_on_invalid_attribute_name(self, dbsession: Session,
                                             authorized_client: TestClient):
        data = {
            "name": "Test",
            "slug": "test",
            "attributes": self.default_attributes + [{
                "name": '403',
                "type": "INT",
                "required": True,
                "unique": False,
                "list": False,
                "key": True,
                "description": 'Age of this person'
            }]
        }

        response = authorized_client.put('/schema/1', json=data)
        assert response.status_code == 422

        schema = dbsession.query(Schema).get(1)
        assert schema.name == "Person"
        assert schema.slug == "person"


class TestRouteSchemaDelete:
    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_delete(self, dbsession: Session, authorized_client: TestClient, id_or_slug):
        response = authorized_client.delete(f'/schema/{id_or_slug}')
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'name': 'Person', 'slug': 'person', 'deleted': True, 'reviewable': False}

    @pytest.mark.parametrize('id_or_slug', [1, 'person'])
    def test_raise_on_already_deleted(self, dbsession: Session, authorized_client: TestClient, id_or_slug):
        dbsession.execute(update(Schema).where(Schema.id == 1).values(deleted=True))
        dbsession.commit()
        response = authorized_client.delete(f'/schema/{id_or_slug}')
        assert response.status_code == 404

    @pytest.mark.parametrize('id_or_slug', [1234567, 'qwerty'])
    def test_raise_on_delete_nonexistent(self, dbsession, authorized_client, id_or_slug):
        response = authorized_client.delete(f'/schema/{id_or_slug}')
        assert response.status_code == 404


class TestRouteGetEntityChanges:
    default_request_data = {
        "name": "Jackson",
        "age": 42,
        "fav_color": ['violet', 'cyan']
    }

    def test_get_recent_changes(self, dbsession: Session, client: TestClient, testuser: User):
        response = client.get('/changes/entity/person/Jack?size=1')
        changes = response.json()
        parsed_timestamp = parser.parse(changes["items"][0]['created_at'])
        assert parsed_timestamp.tzinfo is not None

    def test_get_update_details(self, dbsession: Session, client: TestClient, testuser: User):
        user = dbsession.execute(select(User)).scalar()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        change_request = create_entity_update_request(
            db=dbsession, id_or_slug=1, schema_id=1, data=self.default_request_data.copy(),
            created_by=testuser
        )

        url = f'/changes/detail/entity/{change_request.id}'
        response = client.get(url)
        change = response.json()
        assert change['status'] == 'PENDING'

        dbsession.execute(update(ChangeRequest).values(status=ChangeStatus.APPROVED))
        dbsession.commit()

        response = client.get(url)
        change = response.json()
        assert change['status'] == 'APPROVED'

        dbsession.execute(update(ChangeRequest).values(status=ChangeStatus.DECLINED))
        dbsession.commit()

        response = client.get(url)
        change = response.json()
        assert change['status'] == 'DECLINED'

    def test_get_create_details(self, dbsession: Session, client: TestClient, testuser: User):
        data = self.default_request_data.copy()
        data.update({"slug": "jackson", "age": 42, "friends": [2]})
        change_request = create_entity_create_request(
            db=dbsession, schema_id=1, data=data.copy(),
            created_by=testuser)

        url = f'/changes/detail/entity/{change_request.id}'
        response = client.get(url)
        change = response.json()
        assert change['status'] == 'PENDING'
        assert change['entity']['name'] == ''
        assert change['entity']['slug'] == ''
        assert change['entity']['schema'] == 'person'

        dbsession.execute(update(ChangeRequest).values(status=ChangeStatus.DECLINED))
        dbsession.commit()

        response = client.get(f'/changes/detail/entity/{change_request.id}')
        change = response.json()
        assert change['status'] == 'DECLINED'
        assert change['entity']['name'] == ''
        assert change['entity']['slug'] == ''
        assert change['entity']['schema'] == 'person'

    def test_get_delete_details(self, dbsession: Session, client: TestClient, testuser: User):
        now = datetime.now(timezone.utc)
        change_request = create_entity_delete_request(db=dbsession, id_or_slug=1, schema_id=1,
                                                      created_by=testuser)

        response = client.get(f'/changes/detail/entity/{change_request.id}')
        change = response.json()
        assert parser.parse(change['created_at']) >= now
        assert change['created_by'] == testuser.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change['entity']['name'] == 'Jack'
        assert change['entity']['slug'] == 'Jack'
        assert change['entity']['schema'] == 'person'
        assert len(change['changes']) == 1
        deleted = change['changes']['deleted']
        assert deleted['new'] and not deleted['old'] and not deleted['current']

    def test_raise_on_change_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/detail/entity/12345678')
        assert response.status_code == 404


class TestRouteGetSchemaChanges:
    def test_get_recent_changes(self, dbsession: Session, client: TestClient, testuser: User):
        response = client.get('/changes/schema/person?size=1')
        changes = response.json()
        assert changes["items"][0]['created_at'] is not None

        response = client.get('/changes/schema/person')
        changes = response.json()
        assert sum(1 for i in changes["items"] if i["object_type"] == "ENTITY") == 1
        assert all(change['created_at'] is not None for change in changes['items'])

    def test_get_update_details(self, dbsession: Session, client: TestClient, testuser: User):
        change_request = create_schema_update_request(
            db=dbsession, id_or_slug="person", data=SchemaUpdateSchema(name="Hello", attributes=[]),
            created_by=testuser
        )
        response = client.get(f'/changes/detail/schema/{change_request.id}')
        assert response.status_code == 200
        change = response.json()
        assert change['created_at'] is not None
        assert change['created_by'] == testuser.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change['schema']['name'] == 'Person'
        assert change['schema']['slug'] == 'person'
        assert change['changes']['name']["new"] == "Hello"

    def test_get_create_details(self, dbsession: Session, client: TestClient, testuser: User):
        change_request = create_schema_create_request(
            db=dbsession,
            data=SchemaCreateSchema(name="Test", slug="test", attributes=[]),
            created_by=testuser
        )
        response = client.get(f'/changes/detail/schema/{change_request.id}')
        assert response.status_code == 200
        change = response.json()

        assert change['created_at'] is not None
        assert change['created_by'] == testuser.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert change["schema"] is None

    def test_get_delete_details(self, dbsession: Session, authorized_client: TestClient,
                                testuser: User):
        change_request = create_schema_delete_request(db=dbsession, id_or_slug="person",
                                                      created_by=testuser)
        response = authorized_client.get(f'/changes/detail/schema/{change_request.id}')
        assert response.status_code == 200
        change = response.json()

        assert change['created_at'] is not None
        assert change['created_by'] == testuser.username
        assert change['reviewed_at'] == change['reviewed_by'] == change['comment'] == None
        assert change['status'] == 'PENDING'
        assert len(change['changes']) == 1
        deleted = change['changes']['deleted']
        assert deleted['new'] is True and deleted['old'] is False and  deleted['current'] is False

    def test_raise_on_change_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get('/changes/schema/12345678')
        assert response.status_code == 404


class TestTraceabilityRoutes:
    def test_review_changes(self, dbsession: Session, authorized_client: TestClient,
                            testuser: User):
        data = {"name": "Føø Bar"}
        change_request = create_entity_update_request(
            db=dbsession, id_or_slug=1, schema_id=1, data=data.copy(), created_by=testuser
        )

        # APPROVE
        review = {
            'result': 'APPROVE',
            'comment': 'test'
        }

        response = authorized_client.post(f'/changes/review/{change_request.id}', json=review)
        assert response.status_code == 200
        data = response.json()
        expected = {
            'created_by': 'tester', 'reviewed_by': 'tester', 'status': 'APPROVED',
            'comment': 'test', 'object_type': 'ENTITY', 'change_type': 'UPDATE'
        }
        for key, value in expected.items():
            assert data.get(key, None) == value

        dbsession.commit()
        change_request.status = ChangeStatus.PENDING
        dbsession.commit()

        # DECLINE
        review['result'] = 'DECLINE'
        review['comment'] = 'test2'
        response = authorized_client.post(f'/changes/review/{change_request.id}', json=review)
        json = response.json()
        assert json['status'] == 'DECLINED'
        assert json['comment'] == 'test2'

    def test_raise_on_change_doesnt_exist(self, dbsession: Session, authorized_client: TestClient):
        review = {
            'result': 'APPROVE',
            'comment': 'test'
        }
        response = authorized_client.post('/changes/review/23456', json=review)
        assert response.status_code == 404
