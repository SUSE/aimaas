import json
from fastapi.testclient import TestClient

from backend.tests.test_traceability import make_change_for_review

from ..models import *
from ..schemas import *
from .test_auth import make_group, gen_users, asserts_after_create_group, asserts_after_update_group_first, asserts_after_update_group_second


def test_get_groups(dbsession: Session, client: TestClient):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    response = client.get('/groups')
    test1.id, test1.name, test2.id, test2.name  # w/o this line below `behaves like these objects don't have `id` and `name` fields
    assert response.json() == [GroupSchema(**test1.__dict__), GroupSchema(**test2.__dict__)]


def test_create_group(dbsession: Session, client: TestClient):
    users = gen_users(10, dbsession)
    data = CreateGroupSchema(
        name='test',
        permissions=[
            PermissionSchema(
                obj=PermObject.SCHEMA,
                type=PermType.CREATE_ENTITIES
            ),
            PermissionSchema(
                obj_id=1,
                obj=PermObject.ENTITY,
                type=PermType.UPDATE
            )
        ],
        members=[i.id for i in users]
    )
    dbsession.commit()
    response = client.post('/groups', json=json.loads(data.json()))
    group = response.json()
    assert group['name'] == 'test' and group['parent_id'] is None
    
    data = CreateGroupSchema(name='test2', permissions=[], members=[], parent_id=group['id'])
    response = client.post('/groups', json=json.loads(data.json()))
    group2 = response.json()
    assert group2['name'] == 'test2' and group2['parent_id'] == group['id']
    asserts_after_create_group(dbsession, Group(**group), Group(**group2), users)


def test_create_group_raise_on_already_exists(dbsession: Session, client: TestClient):
    data = CreateGroupSchema(name='test', permissions=[], members=[])
    response = client.post('/groups', json=json.loads(data.json()))
    assert response.status_code == 200
    response = client.post('/groups', json=json.loads(data.json()))
    assert response.status_code == 409


def test_create_group_raise_on_user_doesnt_exist(dbsession: Session, client: TestClient):
    data = CreateGroupSchema(name='test', permissions=[], members=[999])
    response = client.post('/groups', json=json.loads(data.json()))
    assert response.status_code == 404


def test_get_group_details(dbsession: Session, client: TestClient):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    test2.parent_id = test1.id
    dbsession.commit()
    response = client.get(f'groups/{test1.id}')
    details = response.json()
    assert details['name'] == 'test1'
    assert details['member_count'] == 1
    assert len(details['children']) == 1
    assert details['children'][0]['name'] == 'test2'
    assert len(details['permissions']) == 1
    perm = details['permissions'][0]
    assert PermissionSchema(obj=PermObject.SCHEMA, type=PermType.CREATE) == PermissionSchema(**perm)


def test_get_grp_det_raise_on_grp_doesnt_exist(dbsession: Session, client: TestClient):
    response = client.get(f'groups/999999')
    assert response.status_code == 404


def test_get_group_members(dbsession: Session, client: TestClient):
    group = make_group('group', dbsession)
    users = gen_users(10, dbsession)
    for u in users:
        dbsession.add(UserGroup(group=group, user=u))
    dbsession.commit()

    response = client.get(f'groups/{group.id}/members')
    members = response.json()
    assert {i['id'] for i in members[1:]} == {i.id for i in users}
    assert members[0]['username'] == 'admin'


def test_get_grp_members_raise_on_grp_doesnt_exist(dbsession: Session, client: TestClient):
    response = client.get(f'groups/999999/mermbers')
    assert response.status_code == 404


def test_update_group(dbsession: Session, client: TestClient):
    users = gen_users(10, dbsession)
    group = make_group(name='test', db=dbsession)
    dbsession.commit()
    data = UpdateGroupSchema(
        name='test2',
        add_permissions=[
            PermissionSchema(
                obj=PermObject.SCHEMA,
                type=PermType.UPDATE
            ),
            PermissionSchema(
                obj_id=1,
                obj=PermObject.ENTITY,
                type=PermType.DELETE
            )
        ],
        delete_permissions=[
            PermissionSchema(
                obj=PermObject.SCHEMA,
                type=PermType.CREATE
            )
        ],
        add_users=[i.id for i in users],
        delete_users=[1]
    )
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    updated = response.json()
    assert updated['id'] == group.id
    assert updated['name'] == 'test2'
    asserts_after_update_group_first(dbsession, group, Group(**updated), data.add_permissions, users)
    
    # just update users
    data = UpdateGroupSchema(delete_users=[i.id for i in users], add_users=[1])
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    updated = response.json()
    assert updated['id'] == group.id
    assert updated['name'] == 'test2'
    asserts_after_update_group_second(dbsession, group, Group(**updated))


def test_upd_grp_raise_on_group_cycle(dbsession: Session, client: TestClient):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    test2.parent_id = test1.id
    dbsession.commit()
    data = UpdateGroupSchema(parent_id=test2.id) # 1 ← 2 ← 1
    response = client.put(f'/groups/{test1.id}', json=json.loads(data.json()))
    assert response.status_code == 409
    assert response.json()['detail'] == 'Made an attempt to inherit from group which either directly or indirectly inherits from current group'
    
    test3 = make_group('test3', dbsession)
    test2.parent_id = test1.id
    test3.parent_id = test2.id
    dbsession.commit()
    data = UpdateGroupSchema(parent_id=test3.id)  # 1 ← 2 ← 3 ← 1
    response = client.put(f'/groups/{test1.id}', json=json.loads(data.json()))
    assert response.status_code == 409
    assert response.json()['detail'] == 'Made an attempt to inherit from group which either directly or indirectly inherits from current group'


def test_upd_grp_raise_on_name_exists(dbsession: Session, client: TestClient):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    dbsession.commit()
    data = UpdateGroupSchema(name='test1')
    response = client.put(f'/groups/{test2.id}', json=json.loads(data.json()))
    assert response.status_code == 409
    assert 'already exists' in response.json()['detail']


def test_upd_grp_raise_on_remove_missing_permission(dbsession: Session, client: TestClient):
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

    
def test_upd_grp_raise_on_remove_permission_not_defined_on_group(dbsession: Session, client: TestClient):
    group = make_group('test', dbsession)
    perm = Permission(obj=PermObject.SCHEMA, type=PermType.UPDATE)
    dbsession.add(perm)
    dbsession.commit()
    data = UpdateGroupSchema(delete_permissions=[
        PermissionSchema(
                obj=PermObject.SCHEMA,
                type=PermType.UPDATE
            )
    ])
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    assert response.status_code == 404


def test_upd_grp_raise_on_add_missing_user(dbsession: Session, client: TestClient):
    group = make_group('test', dbsession)
    dbsession.commit()
    data = UpdateGroupSchema(add_users=[9999])
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    assert response.status_code == 404


def test_upd_grp_raise_on_remove_missing_user(dbsession: Session, client: TestClient):
    group = make_group('test', dbsession)
    dbsession.commit()
    data = UpdateGroupSchema(delete_users=[9999])
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    assert response.status_code == 404

def test_upd_grp_raise_on_remove_user_not_present_in_this_group(dbsession: Session, client: TestClient):
    group = make_group('test', dbsession)
    user = User(username='test', email='test', password='test')
    dbsession.add(user)
    dbsession.commit()
    data = UpdateGroupSchema(delete_users=[user.id])
    response = client.put(f'/groups/{group.id}', json=json.loads(data.json()))
    assert response.status_code == 404


def test_login(dbsession: Session, client: TestClient):
    response = client.post('/login', data={'username': 'admin', 'password': 'admin'})
    assert response.json()['access_token']

def test_login_raise_on_invalid_cred(dbsession: Session, client: TestClient):
    response = client.post('/login', data={'username': 'admin', 'password': 'qwe'})
    assert response.status_code == 401

    response = client.post('/login', data={'username': 'qwe', 'password': 'qwe'})
    assert response.status_code == 401