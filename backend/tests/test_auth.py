import pytest
from jose import jwt
from sqlalchemy.sql.expression import delete

from ..auth import *
from ..schemas.auth import *
from ..models import *


def gen_users(count: int, db: Session):
    users = []
    for i in range(count):
        user = User(username=f'user_{i}', email=f'user_{i}@example.com', password='test')
        users.append(user)
        db.add(user)
    db.flush()
    return users


def asserts_after_create_group(db: Session, group: Group, group2: Group, users: List[User]):
    assert group.name == 'test' and group.parent_id is None
    group_perms = db.execute(select(GroupPermission).where(GroupPermission.group_id == group.id)).scalars().all()
    assert len(group_perms) == 2
    perm1, perm2 = [i.permission for i in group_perms]
    assert perm1.obj_id is None and perm1.obj == PermObject.SCHEMA and perm1.type == PermType.CREATE_ENTITIES
    assert perm2.obj_id == 1 and perm2.obj == PermObject.ENTITY and perm2.type == PermType.UPDATE

    group_users = db.execute(select(UserGroup).where(UserGroup.group_id == group.id)).scalars().all()
    assert len(group_users) == len(users)
    assert {i.user_id for i in group_users} == {i.id for i in users} 

    assert group2.name == 'test2' and group2.parent_id == group.id
    group_perms = db.execute(select(GroupPermission).where(GroupPermission.group_id == group2.id)).scalars().all()
    group_users = db.execute(select(UserGroup).where(UserGroup.group_id == group2.id)).scalars().all()
    assert not group_perms and not group_users


def test_create_group(dbsession: Session):
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
    group = create_group(db=dbsession, data=data)
    data = CreateGroupSchema(name='test2', permissions=[], members=[], parent_id=group.id)
    group2 = create_group(db=dbsession, data=data)
    asserts_after_create_group(dbsession, group, group2, users)


def test_create_group_raise_on_already_exists(dbsession: Session):
    data = CreateGroupSchema(name='test', permissions=[], members=[])
    create_group(db=dbsession, data=data)
    with pytest.raises(GroupExistsException):
        create_group(db=dbsession, data=data)


def test_create_group_raise_on_user_doesnt_exist(dbsession: Session):
    data = CreateGroupSchema(name='test', permissions=[], members=[999])
    with pytest.raises(MissingUserException):
        create_group(db=dbsession, data=data)


def test_get_user_by_id(dbsession: Session):
    users = gen_users(10, dbsession)
    for i in range(len(users)):
        assert get_user_by_id(users[i].id, dbsession) == users[i]
    assert get_user_by_id(999999999, dbsession) is None

def make_group(name: str, db: Session):
    group = Group(name=name)
    perm = Permission(obj=PermObject.SCHEMA, type=PermType.CREATE)
    group_perm = GroupPermission(group=group, permission=perm)
    group_user = UserGroup(group=group, user_id=1)
    db.add_all([group, perm, group_perm, group_user])
    db.commit()
    return group
    

def asserts_after_update_group_first(db: Session, group: Group, updated: Group, new_permissions, users: List[User]):
    assert updated.id == group.id
    assert updated.name == 'test2'

    perms = db.execute(select(GroupPermission).where(GroupPermission.group_id == updated.id)).scalars().all()
    assert len(perms) == 2
    assert {PermissionSchema(**i.permission.__dict__) for i in perms} == {i for i in new_permissions}

    group_users = db.execute(select(UserGroup).where(UserGroup.group_id == updated.id)).scalars().all()
    assert len(group_users) == 10
    group_users = [i.user_id for i in group_users]
    assert 1 not in group_users
    assert group_users == [i.id for i in users]
    user_1 = db.execute(select(User).where(User.id == 1)).scalar()
    assert user_1 is not None, 'This user must still be present in DB'


def asserts_after_update_group_second(db: Session, group: Group, updated: Group):
    # just update users
    assert updated.id == group.id
    assert updated.name == 'test2'
    perms = db.execute(select(GroupPermission).where(GroupPermission.group_id == updated.id)).scalars().all()
    assert len(perms) == 2
    group_users = db.execute(select(UserGroup).where(UserGroup.group_id == updated.id)).scalars().all()
    assert len(group_users) == 1


def test_update_group(dbsession: Session):
    users = gen_users(10, dbsession)
    group = make_group(name='test', db=dbsession)
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
    updated = update_group(group_id=group.id, data=data, db=dbsession)
    asserts_after_update_group_first(dbsession, group, updated, data.add_permissions, users)

    # just update users
    data2 = UpdateGroupSchema(delete_users=[i.id for i in users], add_users=[1])
    updated2 = update_group(group_id=updated.id, data=data2, db=dbsession)
    asserts_after_update_group_second(dbsession, group, updated2)


def test_upd_grp_raise_on_group_cycle(dbsession: Session):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    test2.parent_id = test1.id
    data = UpdateGroupSchema(parent_id=test2.id) # 1 ← 2 ← 1
    with pytest.raises(CircularGroupReferenceException):
        update_group(group_id=test1.id, data=data, db=dbsession)

    test3 = make_group('test3', dbsession)
    test2.parent_id = test1.id
    test3.parent_id = test2.id
    data = UpdateGroupSchema(parent_id=test3.id)  # 1 ← 2 ← 3 ← 1
    with pytest.raises(CircularGroupReferenceException):
        update_group(group_id=test1.id, data=data, db=dbsession)


def test_upd_grp_raise_on_name_exists(dbsession: Session):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    data = UpdateGroupSchema(name='test1')
    with pytest.raises(GroupExistsException):
        update_group(group_id=test2.id, data=data, db=dbsession)


def test_upd_grp_raise_on_remove_missing_permission(dbsession: Session):
    group = make_group('test', dbsession)
    data = UpdateGroupSchema(delete_permissions=[
        PermissionSchema(
                obj=PermObject.SCHEMA,
                type=PermType.UPDATE
            )
    ])
    with pytest.raises(MissingPermissionException):
        update_group(group.id, data, dbsession)

    
def test_upd_grp_raise_on_remove_permission_not_defined_on_group(dbsession: Session):
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
    with pytest.raises(MissingGroupPermissionException):
        update_group(group.id, data, dbsession)


def test_upd_grp_raise_on_add_missing_user(dbsession: Session):
    group = make_group('test', dbsession)
    data = UpdateGroupSchema(add_users=[9999])
    with pytest.raises(MissingUserException):
        update_group(group.id, data, dbsession)


def test_upd_grp_raise_on_remove_missing_user(dbsession: Session):
    group = make_group('test', dbsession)
    data = UpdateGroupSchema(delete_users=[9999])
    with pytest.raises(MissingUserException):
        update_group(group.id, data, dbsession)

def test_upd_grp_raise_on_remove_user_not_present_in_this_group(dbsession: Session):
    group = make_group('test', dbsession)
    user = User(username='test', email='test', password='test')
    dbsession.add(user)
    dbsession.flush()
    data = UpdateGroupSchema(delete_users=[user.id])
    with pytest.raises(MissingUserGroupException):
        update_group(group.id, data, dbsession)


def test_get_permission(dbsession: Session):
    perm = Permission(obj=PermObject.SCHEMA, type=PermType.UPDATE, obj_id=999)
    dbsession.add(perm)
    dbsession.flush()

    db_perm = get_permission(PermissionSchema(**perm.__dict__), dbsession)
    assert perm == db_perm

    data = PermissionSchema(obj_id=100, obj=PermObject.ENTITY, type=PermType.UPDATE_ENTITIES)
    perm = get_permission(data, dbsession)
    assert perm is None   

def test_create_or_get_permission(dbsession: Session):
    perm = Permission(obj=PermObject.SCHEMA, type=PermType.UPDATE, obj_id=999)
    dbsession.add(perm)
    dbsession.flush()

    db_perm = create_or_get_permission(PermissionSchema(**perm.__dict__), dbsession)
    assert perm == db_perm

    data = PermissionSchema(obj_id=100, obj=PermObject.ENTITY, type=PermType.UPDATE_ENTITIES)
    db_perm = create_or_get_permission(data, dbsession)
    assert db_perm.obj and db_perm.type
    assert PermissionSchema(**db_perm.__dict__) == data


def test_get_group(dbsession: Session):
    group = make_group('test', dbsession)
    db_group = get_group(group.id, dbsession)
    assert group == db_group
    assert get_group(999, dbsession) is None


def test_get_group_or_raise(dbsession: Session):
    group = make_group('test', dbsession)
    db_group = get_group_or_raise(group.id, dbsession)
    assert group == db_group
    with pytest.raises(MissingGroupException):
        get_group_or_raise(999, dbsession)


def test_get_group_details(dbsession: Session):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    test2.parent_id = test1.id
    dbsession.flush()
    details = get_group_details(group_id=test1.id, db=dbsession)
    assert details.name == 'test1'
    assert details.member_count == 1
    assert len(details.children) == 1
    assert details.children[0].name == 'test2'
    assert len(details.permissions) == 1
    perm = details.permissions[0]
    assert PermissionSchema(obj=PermObject.SCHEMA, type=PermType.CREATE) == PermissionSchema(**perm.__dict__)


def test_get_grp_det_raise_on_grp_doesnt_exist(dbsession: Session):
    with pytest.raises(MissingGroupException):
        get_group_details(999, dbsession)


def test_get_group_members(dbsession: Session):
    group = make_group('group', dbsession)
    users = gen_users(10, dbsession)
    for u in users:
        dbsession.add(UserGroup(group=group, user=u))
    dbsession.flush()

    members = get_group_members(group.id, dbsession)
    assert members[1:] == users
    assert members[0].username == 'admin'


def test_get_grp_members_raise_on_grp_doesnt_exist(dbsession: Session):
    with pytest.raises(MissingGroupException):
        get_group_members(999, dbsession)


def test_get_groups(dbsession: Session):
    test1 = make_group('test1', dbsession)
    test2 = make_group('test2', dbsession)
    assert get_groups(dbsession) == [test1, test2]


def test_get_password_hash_and_verify_password():
    pwd = 'test'
    hash_ = get_password_hash(pwd)
    assert verify_password(pwd, hash_)
    assert not verify_password('foo', hash_)


def test_get_user(dbsession: Session):
    user = dbsession.execute(select(User)).scalar()
    assert user == get_user(db=dbsession, username=user.username)
    assert get_user(username='qwerty', db=dbsession) is None


def test_authenticate_user(dbsession: Session):
    user = dbsession.execute(select(User)).scalar()
    assert user.password != 'admin', 'It should be equal to its hash'
    db_user = authenticate_user(db=dbsession, username='admin', password='admin')
    assert user == db_user

    db_user = authenticate_user(db=dbsession, username='Doesnt exist', password='admin')
    assert db_user is None

    db_user = authenticate_user(db=dbsession, username='admin', password='Wrong password')
    assert db_user is None


def test_create_access_token_and_get_current_user(dbsession: Session):
    import time
    from ..config import settings as s
    token = create_access_token(data={'foo': 'bar', 'sub': 'admin'}, expires_delta=timedelta(hours=3))
    data = jwt.decode(token, s.secret, algorithms=[s.pwd_hash_alg])
    assert data['foo'] == 'bar' and data['sub'] == 'admin'
    expire_in = data['exp']
    delta = expire_in - time.time()  # must be close to 3 hours
    # 10800 is 3 hours in seconds; I'm checking
    # not exactly 10800 because by this line
    # some time may have already passed
    assert 10700 <= delta <= 10800

    user = dbsession.execute(select(User)).scalar()
    db_user = get_current_user(db=dbsession, token=token)
    assert user == db_user


def test_get_cur_user_raise_on_username_not_provided(dbsession: Session):
    token = create_access_token(data={'foo': 'bar'}, expires_delta=timedelta(hours=3))
    with pytest.raises(HTTPException):
        get_current_user(db=dbsession, token=token)


def test_get_cur_user_raise_on_bad_token(dbsession: Session):
    with pytest.raises(HTTPException):
        get_current_user(db=dbsession, token='qwerty')


def test_get_cur_user_raise_on_missing_user(dbsession: Session):
    token = create_access_token(data={'sub': 'sub'}, expires_delta=timedelta(hours=3))
    with pytest.raises(HTTPException):
        get_current_user(db=dbsession, token=token)


def make_groups_tree(db: Session):
    '''
    Builds following group hierarchy
            A(3)         J
           /   \         |
          B(2)  C(1)    [K]
         / \    / \      |
        D  [E]  F  G     L(5)
        |      |
        H(4)  [I]

    Notation A(3) means that we assign permission #3 to Group A
    Notation [E] means that user is member of Group E
    At the moment I'm writing this the idea is that a group
    inherits permissions from parent groups, e.g. Group E inherits from A and B,
    Group I - from F, C and A    
    '''
    group_a = make_group('Group A', db=db)
    group_b = make_group('Group B', db=db)
    group_c = make_group('Group C', db=db)
    group_d = make_group('Group D', db=db)
    group_e = make_group('Group E', db=db)
    group_f = make_group('Group F', db=db)
    group_g = make_group('Group G', db=db)
    group_h = make_group('Group H', db=db)
    group_i = make_group('Group I', db=db)
    group_j = make_group('Group J', db=db)
    group_k = make_group('Group K', db=db)
    group_l = make_group('Group L', db=db)

    group_b.parent = group_a
    group_d.parent = group_b
    group_h.parent = group_d
    group_e.parent = group_b

    group_c.parent = group_a
    group_f.parent = group_c
    group_i.parent = group_f
    group_g.parent = group_c

    group_k.parent = group_j
    group_l.parent = group_k
    db.flush()

    perm_1 = Permission(obj=PermObject.ENTITY, type=PermType.UPDATE)
    perm_2 = Permission(obj=PermObject.ENTITY, type=PermType.UPDATE, obj_id=2)
    perm_3 = Permission(obj=PermObject.SCHEMA, type=PermType.UPDATE_ENTITIES, obj_id=3)
    perm_4 = Permission(obj=PermObject.SCHEMA, type=PermType.UPDATE_ENTITIES)
    perm_5 = Permission(obj=PermObject.ENTITY, type=PermType.CREATE_ENTITIES)

    gp1 = GroupPermission(group=group_c, permission=perm_1)
    gp2 = GroupPermission(group=group_b, permission=perm_2)
    gp3 = GroupPermission(group=group_a, permission=perm_3)
    gp4 = GroupPermission(group=group_h, permission=perm_4)
    gp5 = GroupPermission(group=group_l, permission=perm_5)

    user = db.execute(select(User)).scalar()
    db.execute(delete(UserGroup))
    user_e = UserGroup(user=user, group=group_e)
    user_i = UserGroup(user=user, group=group_i)
    user_k = UserGroup(user=user, group=group_k)

    db.add_all([
        group_a, group_b, group_c, group_d, 
        group_e, group_f, group_g, group_h, 
        group_i, group_j, group_k,
        perm_1, perm_2, perm_3, perm_4, perm_5,
        gp1, gp2, gp3, gp4, gp5,
        user_e, user_i, user_k
    ])
    db.flush()
    return perm_1, perm_2, perm_3, perm_4, perm_5

def test_check_has_perm_in_groups(dbsession: Session):
    perm_1, perm_2, perm_3, perm_4, perm_5 = make_groups_tree(dbsession)
    user = dbsession.execute(select(User)).scalar()

    assert check_has_perm_in_groups(perm_1, user, dbsession)
    assert check_has_perm_in_groups(perm_2, user, dbsession)
    assert check_has_perm_in_groups(perm_3, user, dbsession)
    assert not check_has_perm_in_groups(perm_4, user, dbsession)
    assert not check_has_perm_in_groups(perm_5, user, dbsession)


def make_perms_for_user(user: User, db: Session):
    perm = Permission(obj=PermObject.ENTITY, type=PermType.CREATE)
    perm2 = Permission(obj=PermObject.ENTITY, type=PermType.CREATE_ENTITIES)
    user_perm = UserPermission(user=user, permission=perm)
    db.add_all([perm, user_perm, perm2])
    db.flush()
    return perm, perm2


def test_check_user_has_perm(dbsession: Session):
    user = dbsession.execute(select(User)).scalar()
    perm, perm2 = make_perms_for_user(user, dbsession)
    assert check_user_has_perm(perm, user, dbsession)
    assert not check_user_has_perm(perm2, user, dbsession)


def test_check_is_authorized(dbsession: Session):
    user = dbsession.execute(select(User)).scalar()
    # permission is in groups
    perm_1, perm_2, perm_3, perm_4, perm_5 = make_groups_tree(dbsession)
    assert is_authorized(perm_1.type, perm_1.obj, user, dbsession, perm_1.obj_id)
    assert is_authorized(perm_2.type, perm_2.obj, user, dbsession, perm_2.obj_id)
    assert is_authorized(perm_3.type, perm_3.obj, user, dbsession, perm_3.obj_id)
    assert not is_authorized(perm_4.type, perm_4.obj, user, dbsession, perm_4.obj_id)
    assert not is_authorized(perm_5.type, perm_5.obj, user, dbsession, perm_5.obj_id)

    # permission is assigned to user directly
    perm_1, perm_2 = make_perms_for_user(user, dbsession)
    assert is_authorized(perm_1.type, perm_1.obj, user, dbsession, perm_1.obj_id)
    assert not is_authorized(perm_2.type, perm_2.obj, user, dbsession, perm_2.obj_id)
