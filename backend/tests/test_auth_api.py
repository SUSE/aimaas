import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ..auth import authenticate_user
from ..auth.crud import add_members, has_permission
from ..auth.enum import RecipientType, PermissionTargetType, PermissionType
from ..auth.models import User, Permission, Group
from ..config import settings
from ..models import Schema, Entity
from ..schemas import BaseGroupSchema, GroupSchema, UserCreateSchema, PermissionSchema, \
    RequirePermission
from .conftest import TEST_USER
from .mixins import CreateMixin


def _override_settings():
    # Make sure that only the local auth. backend is used!
    settings.auth_backends = "local"


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

    def test_delete_group(self, dbsession: Session, authorized_client: TestClient):
        group = self._create_group(dbsession)
        response = authorized_client.delete(f"/groups/{group.id}")
        assert response.status_code == 200
        assert dbsession.query(Group.id).filter(Group.id == group.id).count() == 0

    def test_delete_group__raise_on_parent_exists(self, dbsession: Session, authorized_client: TestClient):
        user, group, pgroup = self._create_user_group_with_perm(dbsession)
        response = authorized_client.delete(f"/groups/{pgroup.id}")
        dbsession.refresh(group)
        assert group.parent_id == pgroup.id
        assert dbsession.query(Group.id).filter(Group.id == group.id).count() == 1
        assert dbsession.query(Group.id).filter(Group.id == pgroup.id).count() == 1
        assert response.status_code == 409

    def test_delete_group__with_members(self, dbsession: Session, authorized_client: TestClient):
        user, group, pgroup = self._create_user_group_with_perm(dbsession)
        response = authorized_client.delete(f"/groups/{group.id}")
        assert response.status_code == 200
        assert dbsession.query(Group.id).filter(Group.id == group.id).count() == 0
        dbsession.refresh(user)
        assert len(user.groups) == 0

    def test_delete_group__raise_on_doesnt_exist(self, dbsession: Session, authorized_client: TestClient):
        response = authorized_client.delete("/groups/9999")
        assert response.status_code == 404


class TestRouteUser(CreateMixin):
    def test_get_users(self, dbsession: Session, authenticated_client: TestClient):
        response = authenticated_client.get("/users")
        assert response.status_code == 200
        assert {u["username"] for u in response.json()} == {'tester'}

    def test_get_user_membership(self, dbsession: Session, authenticated_client: TestClient):
        user, group, parent_group = self._create_user_group_with_perm(dbsession)
        response = authenticated_client.get(f"/users/{user.username}/memberships")
        assert response.status_code == 200
        assert {group.name} == {g["name"] for g in response.json()}

    def test_create_user(self, dbsession, client: TestClient):
        data = {"username": "new-user", "email": "new@example.com", "password": "password"}
        response = client.post("/users", json=data)
        assert response.status_code == 200

        _override_settings()
        assert authenticate_user(dbsession, data["username"], data["password"]) is not None

    def test_deactivate_user(self, dbsession: Session, authorized_client: TestClient):
        user = self._create_user(dbsession)

        # Deactivate user
        response = authorized_client.delete(f"/users/{user.username}")
        assert response.status_code == 200
        dbsession.refresh(user)
        assert user.is_active is False

        # Deactivate already deactivated user
        response = authorized_client.delete(f"/users/{user.username}")
        assert response.status_code == 208
        dbsession.refresh(user)
        assert user.is_active is False

    def test_activate_user(self, dbsession: Session, authorized_client: TestClient):
        user = self._create_user(dbsession)

        # Activate already active user
        response = authorized_client.patch(f"/users/{user.username}")
        assert response.status_code == 208
        dbsession.refresh(user)
        assert user.is_active is True

        user.is_active = False
        dbsession.commit()

        # Activate user
        response = authorized_client.patch(f"/users/{user.username}")
        assert response.status_code == 200
        dbsession.refresh(user)
        assert user.is_active is True


class TestRoutePermission(CreateMixin):
    def test_grant_permission(self, dbsession: Session, authorized_client: TestClient):
        user = self._create_user(dbsession)
        schema = self.get_default_schema(dbsession)
        data = PermissionSchema(
            recipient_type=RecipientType.USER,
            recipient_name=user.username,
            obj_type=PermissionTargetType.SCHEMA,
            obj_id=schema.id,
            permission=PermissionType.CREATE_ENTITY
        )

        response = authorized_client.post("/permissions", json=json.loads(data.json()))
        assert response.status_code == 200
        assert has_permission(user,
                              RequirePermission(permission=PermissionType.CREATE_ENTITY,
                                                target=Schema(id=schema.id)),
                              dbsession) is True

    def test_grant_permission__riase_on_already_exists(self, dbsession: Session,
                                                       authorized_client: TestClient):
        user = self._create_user(dbsession)
        schema = self.get_default_schema(dbsession)
        data = PermissionSchema(
            recipient_type=RecipientType.USER,
            recipient_name=user.username,
            obj_type=PermissionTargetType.SCHEMA,
            obj_id=schema.id,
            permission=PermissionType.CREATE_ENTITY
        )
        self._grant_permission(dbsession, data)

        response = authorized_client.post("/permissions", json=json.loads(data.json()))
        assert response.status_code == 208
        assert has_permission(user,
                              RequirePermission(permission=PermissionType.CREATE_ENTITY,
                                                target=Schema(id=schema.id)),
                              dbsession) is True

    def test_grant_permission__raise_on_invalid_recipient(self, dbsession: Session,
                                                          authorized_client: TestClient):
        schema = self.get_default_schema(dbsession)
        data = PermissionSchema(
            recipient_type=RecipientType.USER,
            recipient_name='no-such-username',
            obj_type=PermissionTargetType.SCHEMA,
            obj_id=schema.id,
            permission=PermissionType.CREATE_ENTITY
        )

        response = authorized_client.post("/permissions", json=json.loads(data.json()))
        assert response.status_code == 404

    def test_grant_permission__raise_ob_invalid_target(self, dbsession: Session,
                                                       authorized_client: TestClient):
        user = self._create_user(dbsession)
        data = PermissionSchema(
            recipient_type=RecipientType.USER,
            recipient_name=user.username,
            obj_type=PermissionTargetType.SCHEMA,
            obj_id=9999,
            permission=PermissionType.CREATE_ENTITY
        )

        response = authorized_client.post("/permissions", json=json.loads(data.json()))
        assert response.status_code == 404

    def test_revoke_permission(self, dbsession: Session, authorized_client: TestClient):
        user, group, pgroup = self._create_user_group_with_perm(dbsession)
        entity = self.get_default_entity(dbsession)

        permisison_id = dbsession\
            .query(Permission.id)\
            .filter(Permission.recipient_type == RecipientType.GROUP,
                    Permission.recipient_id == pgroup.id)\
            .scalar()

        response = authorized_client.delete("/permissions", json=[permisison_id])
        assert response.status_code == 200

        assert has_permission(user,
                              RequirePermission(permission=PermissionType.READ_ENTITY,
                                                target=Entity(id=entity.id)),
                              dbsession) is False

    def test_revoke_permission__raise_on_missing(self, dbsession: Session,
                                                 authorized_client: TestClient):
        response = authorized_client.delete("/permissions", json=[9999])
        assert response.status_code == 404


class TestRouteLogin:
    def test_login(self, client: TestClient, testuser: User):
        _override_settings()
        response = client.post('/login', data={'username': TEST_USER.username,
                                               'password': TEST_USER.password})
        assert response.json()['access_token']

    def test_login__raise_on_invalid_cred(self, client: TestClient, testuser: User):
        _override_settings()
        response = client.post('/login', data={'username': TEST_USER.username,
                                               'password': 'this-is-not-my-password'})
        assert response.status_code == 401

        response = client.post('/login', data={'username': 'this-is-no-user',
                                               'password': 'this-could-have-been-a-password'})
        assert response.status_code == 401


class TestRoutesRequiringAuth:
    authenticated = (
        # method, route
        ('post', '/changes/review/1'),
        ('get', '/groups'),
        ('get', '/groups/1'),
        ('get', '/groups/1/members'),
        ('get', '/users'),
        ('get', '/users/tester/memberships'),
        ('get', '/permissions'),
    )
    authorized = (
        ('post', '/schema'),
        ('put', '/schema/unperson'),
        ('delete', '/schema/unperson'),
        ('post', '/groups'),
        ('put', '/groups/1'),
        ('delete', '/groups/1'),
        ('patch', '/groups/1/members'),
        ('delete', '/groups/1/members'),
        ('patch', '/users/tester'),
        ('delete', '/users/tester'),
        ('post', '/permissions'),
        ('delete', '/permissions'),
        ('post', '/entity/person'),
        ('put', '/entity/person/foo'),
        ('delete', '/entity/person/foo'),
    )

    @pytest.mark.parametrize("method, url", authenticated + authorized)
    def test_require_authentication(self, method, url, client: TestClient):
        func = getattr(client, method)
        response = func(url)
        assert response.status_code == 401

    @pytest.mark.parametrize("method, url", authorized)
    def test_require_authorization(self, method, url, dbsession: Session,
                                   unauthorized_testuser: User, authenticated_client: TestClient):
        func = getattr(authenticated_client, method)
        response = func(url)
        assert response.status_code == 403

    def test_review_change_request_breakout__create(self, dbsession: Session,
                                                    unauthorized_testuser: User,
                                                    authenticated_client: TestClient):
        """
        Test that authenticated user is allowed to create a change request without actually creating
        an entity
        """
        response = authenticated_client.post("/entity/unperson",
                                             json={"name": "Foo", "slug": "foo"})
        assert response.status_code == 202
        q = dbsession.query(Entity)\
            .join(Schema)\
            .filter(Schema.slug == "unperson", Entity.slug == "foo")\
            .exists()
        assert not dbsession.query(Entity.id).filter(q).scalar()

    def test_review_change_request_breakout__update(self, dbsession: Session,
                                                    unauthorized_testuser: User,
                                                    authenticated_client: TestClient):
        """
        Test that authenticated user is allowed to create a change request without actually changing
        an entity
        """
        schema = dbsession.query(Schema).where(Schema.slug == "unperson").one()
        entity = Entity(name="Foo", slug="foo", schema_id=schema.id)
        dbsession.add(entity)
        dbsession.commit()
        response = authenticated_client.put("/entity/unperson/foo",
                                            json={"name": "Føø", "slug": "foo"})

        assert response.status_code == 202
        dbsession.refresh(entity)
        assert entity.name == "Foo"

    def test_review_change_request_breakout__delete(self, dbsession: Session,
                                                    unauthorized_testuser: User,
                                                    authenticated_client: TestClient):
        """
        Test that authenticated user is allowed to create a change request without actually deleting
        an entity
        """
        schema = dbsession.query(Schema).where(Schema.slug == "unperson").one()
        entity = Entity(name="Foo", slug="foo", schema_id=schema.id)
        dbsession.add(entity)
        dbsession.commit()
        response = authenticated_client.delete("/entity/unperson/foo",
                                               json={"name": "Føø", "slug": "foo"})

        assert response.status_code == 202
        dbsession.refresh(entity)
        assert entity.name == "Foo"
        assert entity.deleted is False
