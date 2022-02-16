import json
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from .. import auth
from ..auth.backends.local import Backend
from ..auth.crud import add_members
from ..auth.models import User
from ..schemas import BaseGroupSchema, GroupSchema, UserCreateSchema
from .conftest import TEST_USER
from .mixins import CreateMixin


class TestRouteGroup(CreateMixin):
    def test_get_groups(self, dbsession: Session, authenticated_client: TestClient):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2'))
        response = authenticated_client.get('/groups')
        assert response.json() == [GroupSchema(**test1.__dict__), GroupSchema(**test2.__dict__)]

    def test_create_group(self, dbsession: Session, authorized_client: TestClient):
        data = BaseGroupSchema(name='test')
        response = authorized_client.post('/groups', json=json.loads(data.json()))
        group = response.json()
        assert group['name'] == 'test' and group['parent_id'] is None

        data = BaseGroupSchema(name='test2', parent_id=group['id'])
        response = authorized_client.post('/groups', json=json.loads(data.json()))
        group2 = response.json()
        assert group2['name'] == 'test2' and group2['parent_id'] == group['id']

    def test_create_group__raise_on_already_exists(self, dbsession: Session, authorized_client: TestClient):
        data = BaseGroupSchema(name='test')
        response = authorized_client.post('/groups', json=json.loads(data.json()))
        assert response.status_code == 200
        response = authorized_client.post('/groups', json=json.loads(data.json()))
        assert response.status_code == 409

    def test_get_group(self, dbsession: Session, authenticated_client: TestClient):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2', parent_id=test1.id))

        details = authenticated_client.get(f'groups/{test1.id}').json()
        assert details['name'] == test1.name
        assert details["parent_id"] is None

        details = authenticated_client.get(f'groups/{test2.id}').json()
        assert details['name'] == test2.name
        assert details["parent_id"] == test1.id

    def test_get_group__raise_on_doesnt_exist(self, dbsession: Session, authenticated_client: TestClient):
        response = authenticated_client.get(f'groups/999999')
        assert response.status_code == 404

    def test_get_group_members(self, dbsession: Session, authenticated_client: TestClient):
        group = self._create_group(dbsession)
        user1 = self._create_user(dbsession)
        user2 = self._create_user(dbsession, UserCreateSchema(username="testuser-1",
                                                              password="test",
                                                              email="1@example.com"))
        users = [user1, user2]
        add_members(group.id, [u.id for u in users], dbsession)

        response = authenticated_client.get(f'groups/{group.id}/members')
        members = response.json()

        assert {i['id'] for i in members} == {i.id for i in users}

    def test_get_group_members__raise_on_doesnt_exist(self, dbsession: Session, client: TestClient):
        response = client.get(f'groups/999999/mermbers')
        assert response.status_code == 404

    def test_update_group(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        data = BaseGroupSchema(
            name='fancy-new-name',
        )
        response = authorized_client.put(f'/groups/{group.id}', json=json.loads(data.json()))
        updated = response.json()
        assert updated['id'] == group.id
        assert updated['name'] == data.name

    def test_update_group__raise_on_cycle(self, dbsession: Session, authorized_client: TestClient):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name="test2", parent_id=test1.id))

        data = BaseGroupSchema(name=test1.name, parent_id=test2.id)  # 1 ← 2 ← 1
        response = authorized_client.put(f'/groups/{test1.id}', json=json.loads(data.json()))
        assert response.status_code == 409

        test3 = self._create_group(dbsession, BaseGroupSchema(name="test3", parent_id=test2.id))
        data = BaseGroupSchema(name=test1.name, parent_id=test3.id)  # 1 ← 2 ← 3 ← 1
        response = authorized_client.put(f'/groups/{test1.id}', json=json.loads(data.json()))
        assert response.status_code == 409

    def test_update_group__raise_on_name_exists(self, dbsession: Session, authorized_client: TestClient):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2'))
        data = BaseGroupSchema(name=test1.name)
        response = authorized_client.put(f'/groups/{test2.id}', json=json.loads(data.json()))

        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_add_members(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        user = self._create_user(dbsession)

        response = authorized_client.patch(f"/groups/{group.id}/members", json=[user.id])
        assert response.status_code == 200
        dbsession.refresh(group)
        assert len(group.members) == 1

        response = authorized_client.patch(f"/groups/{group.id}/members", json=[user.id])
        assert response.status_code == 208
        dbsession.refresh(group)
        assert len(group.members) == 1

    def test_add_members__raise_on_missing_user(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        assert len(group.members) == 0

        response = authorized_client.patch(f'/groups/{group.id}/members', json=[9999])
        assert response.status_code == 404
        dbsession.refresh(group)
        assert len(group.members) == 0

    def test_remove_member(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        user = self._create_user(dbsession)
        add_members(group.id, [user.id], dbsession)

        response = authorized_client.delete(f"/groups/{group.id}/members", json=[user.id])
        assert response.status_code == 200
        dbsession.refresh(group)
        assert len(group.members) == 0

    def test_remove_member__raise_on_invalid_user(self, dbsession: Session,
                                                  authorized_client: TestClient):
        group = self._create_group(dbsession)
        response = authorized_client.delete(f'/groups/{group.id}/members', json=[9999])
        assert response.status_code == 404

    def test_remove_member__raise_on_no_member(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        user = self._create_user(dbsession)

        response = authorized_client.delete(f'/groups/{group.id}/members', json=[user.id])
        assert response.status_code == 404


class TestRoutePermission(CreateMixin):
    def test_revoke_permission__raise_on_missing(self, dbsession: Session, authorized_client: TestClient):
        group = make_group('test', dbsession)
        dbsession.commit()
        data = UpdateGroupSchema(delete_permissions=[
            PermissionSchema(
                    obj=PermObject.SCHEMA,
                    type=PermType.UPDATE
                )
        ])
        response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
        assert response.status_code == 404


class TestRouteLogin:
    def test_login(self, client: TestClient, testuser: User, mocker: MockerFixture):
        with mocker.patch("backend.auth._enabled_backends", return_value=[]):
            response = client.post('/login', data={'username': TEST_USER.username,
                                                   'password': TEST_USER.password})
        print("===DEBUG===", response.status_code, response.json())
        assert response.json()['access_token']

    def test_login__raise_on_invalid_cred(self, client: TestClient, testuser: User):
        response = client.post('/login', data={'username': TEST_USER.username,
                                               'password': 'this-is-not-my-password'})
        assert response.status_code == 401

        response = client.post('/login', data={'username': 'this-is-no-user',
                                               'password': 'this-could-have-been-a-password'})
        assert response.status_code == 401
