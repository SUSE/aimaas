import pytest
from sqlalchemy.orm import Session

from ..auth.backends.local import Backend
from ..auth.crud import create_group, update_group, get_user_by_id, add_members, \
    delete_members, delete_group, revoke_permissions, get_permissions, has_permission, \
    get_group, get_groups, get_group_or_raise, get_group_details, get_group_members, get_user
from ..auth.enum import RecipientType, PermissionTargetType, PermissionType
from ..auth.models import User, Permission
from .. import exceptions, models
from ..schemas.auth import BaseGroupSchema, UserCreateSchema, PermissionSchema, RequirePermission
from .mixins import CreateMixin


class TestGroup(CreateMixin):
    def test_create_group(self, dbsession: Session):
        group = self._create_group(dbsession)
        assert group.name == 'test' and group.parent_id is None
        perms = dbsession\
            .query(Permission.id)\
            .filter(Permission.recipient_type == RecipientType.GROUP,
                    Permission.recipient_id == group.id)\
            .count()
        assert perms == 0

    def test_create_group_raise_on_already_exists(self, dbsession: Session):
        self._create_group(dbsession)
        with pytest.raises(exceptions.GroupExistsException):
            self._create_group(dbsession)

    def test_update_group__raise_on_cycle(self, dbsession):
        """
        Test that CRUD function allows no circular group relations
        """
        g1 = create_group(data=BaseGroupSchema(name="g1"), db=dbsession)
        g11 = create_group(data=BaseGroupSchema(name="g11", parent_id=g1.id), db=dbsession)
        g111 = create_group(data=BaseGroupSchema(name="g111", parent_id=g11.id), db=dbsession)

        with pytest.raises(expected_exception=exceptions.CircularGroupReferenceException):
            update_group(group_id=g1.id, data=BaseGroupSchema(name=g1.name, parent_id=g111.id),
                         db=dbsession)

    def test_update_group__raise_on_name_exists(self, dbsession: Session):
        test1 = self._create_group(dbsession, BaseGroupSchema(name='test1', parent_id=None))
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2', parent_id=None))
        data = BaseGroupSchema(name='test1')
        with pytest.raises(exceptions.GroupExistsException):
            update_group(group_id=test2.id, data=data, db=dbsession)

    def test_update_group(self, dbsession):
        g2 = create_group(data=BaseGroupSchema(name="g2"), db=dbsession)
        g21 = create_group(data=BaseGroupSchema(name="g21"), db=dbsession)

        assert g21.parent_id is None

        update_group(group_id=g21.id, data=BaseGroupSchema(name="New G11", parent_id=g2.id),
                     db=dbsession)

        assert g21.parent_id == g2.id
        assert g21.name == "New G11"

    def test_add_member(self, dbsession: Session):
        group = self._create_group(dbsession)
        assert len(group.members) == 0

        user = self._create_user(dbsession)

        # Actually add
        result = add_members(group.id, [user.id], dbsession)
        assert result is True
        assert len(group.members) == 1

        # Add again
        result = add_members(group.id, [user.id], dbsession)
        assert result is False
        assert len(group.members) == 1

    def test_add_member__raise_on_missing_user(self, dbsession: Session):
        group = self._create_group(dbsession)
        with pytest.raises(exceptions.MissingUserException):
            add_members(group.id, [9999], dbsession)

    def test_remove_member(self, dbsession: Session):
        group = self._create_group(dbsession)
        user = self._create_user(dbsession)
        assert add_members(group.id, [user.id], dbsession) is True

        result = delete_members(group.id, [user.id], dbsession)
        assert result is True
        assert len(group.members) == 0

    def test_remove_member__raise_on_missing_user(self, dbsession: Session):
        group = self._create_group(dbsession)
        with pytest.raises(exceptions.MissingUserException):
            delete_members(group.id, [9999], dbsession)

    def test_remove_member__not_a_member(self, dbsession: Session):
        group = self._create_group(dbsession)
        user = self._create_user(dbsession)

        with pytest.raises(exceptions.MissingUserGroupException):
            delete_members(group.id, [user.id], dbsession)

    def test_get_group(self, dbsession: Session):
        group = self._create_group(dbsession)
        db_group = get_group(group.id, dbsession)
        assert group == db_group
        assert get_group(999, dbsession) is None

    def test_get_group_or_raise(self, dbsession: Session):
        group = self._create_group(dbsession)
        db_group = get_group_or_raise(group.id, dbsession)
        assert group == db_group
        with pytest.raises(exceptions.MissingGroupException):
            get_group_or_raise(999, dbsession)

    def test_get_group_details(self, dbsession: Session):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2', parent_id=test1.id))

        details = get_group_details(group_id=test1.id, db=dbsession)
        assert details.name == self.default_groupname
        assert details.parent_id is None
        assert details.id == test1.id

        details = get_group_details(group_id=test2.id, db=dbsession)
        assert details.name == 'test2'
        assert details.parent_id == test1.id
        assert details.id == test2.id

    def test_get_group_details__raise_on_doesnt_exist(self, dbsession: Session):
        with pytest.raises(exceptions.MissingGroupException):
            get_group_details(999, dbsession)

    def test_get_group_members(self, dbsession: Session):
        group = self._create_group(dbsession)
        user1 = self._create_user(dbsession)
        user2 = self._create_user(dbsession, UserCreateSchema(username="user-2",
                                                              password="topsecret",
                                                              email="u2@example.com"))
        add_members(group.id, [user1.id, user2.id], dbsession)
        members = get_group_members(group.id, dbsession)
        assert len(members) == 2
        assert set(members) == {user1, user2}

    def test_get_group_members__raise_on_doesnt_exist(self, dbsession: Session):
        with pytest.raises(exceptions.MissingGroupException):
            get_group_members(999, dbsession)

    def test_get_groups(self, dbsession: Session):
        test1 = self._create_group(dbsession)
        test2 = self._create_group(dbsession, BaseGroupSchema(name='test2'))
        assert set(get_groups(dbsession)) == {test1, test2}

    def test_delete_group(self, dbsession: Session):
        group = self._create_group(dbsession)
        assert delete_group(group.id, dbsession) is True

    def test_delete_group__with_members(self, dbsession: Session):
        user, group, pgroup = self._create_user_group_with_perm(dbsession)
        assert delete_group(group.id, dbsession) is True
        dbsession.refresh(user)
        assert len(user.groups) == 0

    def test_delete_group__raise_on_doesnt_exist(self, dbsession: Session):
        with pytest.raises(exceptions.MissingGroupException):
            delete_group(9999, dbsession)


class TestUser(CreateMixin):
    def test_get_user(self, dbsession: Session, testuser: User):
        assert testuser == get_user(db=dbsession, username=testuser.username)
        assert get_user(username='qwerty', db=dbsession) is None

    def test_get_user_by_id(self, dbsession: Session, testuser: User):
        assert get_user_by_id(testuser.id, dbsession) == testuser
        assert get_user_by_id(999999999, dbsession) is None

    def test_authenticate(self, dbsession: Session):
        user = self._create_user(dbsession)
        assert user.password != self.default_password, 'It should be equal to its hash'

        backend = Backend(dbsession)
        db_user = backend.authenticate(username=self.default_username,
                                       password=self.default_password)
        assert user == db_user

        db_user = backend.authenticate(username='Doesnt exist', password='admin')
        assert db_user is None

        db_user = backend.authenticate(username=self.default_username, password='Wrong password')
        assert db_user is None


class TestPermission(CreateMixin):
    def test_grant_permission(self, dbsession: Session):
        result = self._grant_permission(dbsession)
        assert result is True
        r = dbsession.query(Permission.id)\
            .join(Permission.user)\
            .filter(User.username == self.default_username)\
            .count()
        assert r == 1

    def test_grant_permission__raise_on_invalid_user(self, dbsession: Session):
        e = self.get_default_entity(dbsession)
        with pytest.raises(exceptions.MissingUserException):
            self._grant_permission(dbsession, PermissionSchema(
                recipient_type=RecipientType.USER, recipient_name="does-not-exist",
                obj_type=PermissionTargetType.ENTITY, obj_id=e.id,
                permission=PermissionType.UPDATE_ENTITY
            ))

    def test_grant_permisison__raise_on_invalid_object(self, dbsession: Session, testuser: User):
        e = self.get_default_entity(dbsession)
        with pytest.raises(exceptions.MissingObjectException):
            self._grant_permission(dbsession, PermissionSchema(
                recipient_type=RecipientType.USER, recipient_name=testuser.username,
                obj_type=PermissionTargetType.ENTITY, obj_id=9999,
                permission=PermissionType.UPDATE_ENTITY
            ))

        with pytest.raises(ValueError):
             self._grant_permission(dbsession, PermissionSchema(
                recipient_type=RecipientType.USER, recipient_name=testuser.username,
                obj_type=PermissionTargetType.ENTITY, obj_id=None,
                permission=PermissionType.UPDATE_ENTITY
            ))

        with pytest.raises(ValueError):
             self._grant_permission(dbsession, PermissionSchema(
                recipient_type=RecipientType.USER, recipient_name=testuser.username,
                obj_type=None, obj_id=e.id,
                permission=PermissionType.UPDATE_ENTITY
            ))

    def test_get_permissions(self, dbsession: Session):
        user, group, parent_group = self._create_user_group_with_perm(dbsession)

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.USER,
                                recipient_id=user.id)
        assert len(perms) == 4

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.GROUP,
                                recipient_id=group.id)
        assert len(perms) == 3

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.GROUP,
                                recipient_id=parent_group.id)
        assert len(perms) == 1

    def test_has_permission(self, dbsession: Session, testuser: User):
        user, group, parent_group = self._create_user_group_with_perm(dbsession)
        other_user = self._create_user(dbsession, UserCreateSchema(username="nemo",
                                                                   password="secure",
                                                                   email="nemo@example.com"))
        entity = self.get_default_entity(dbsession)

        for perm in (PermissionType.READ_ENTITY, PermissionType.UPDATE_ENTITY):
            req_perm_schema = RequirePermission(permission=perm, target=models.Schema(id=entity.schema_id))
            req_perm_entity = RequirePermission(permission=perm, target=models.Entity(id=entity.id))
            assert has_permission(user, req_perm_schema, dbsession) is True
            assert has_permission(user, req_perm_entity, dbsession) is True
            assert has_permission(other_user, req_perm_schema, dbsession) is False
            assert has_permission(other_user, req_perm_entity, dbsession) is False
            assert has_permission(testuser, req_perm_entity, dbsession) is True

        req_perm = RequirePermission(permission=PermissionType.DELETE_ENTITY,
                                     target=models.Schema(id=entity.schema_id))
        assert has_permission(user, req_perm, dbsession) is False
        assert has_permission(other_user, req_perm, dbsession) is False
        assert has_permission(testuser, req_perm, dbsession) is True

        req_perm = RequirePermission(permission=PermissionType.DELETE_ENTITY,
                                     target=models.Entity(id=entity.id))
        assert has_permission(user, req_perm, dbsession) is True
        assert has_permission(other_user, req_perm, dbsession) is False
        assert has_permission(testuser, req_perm, dbsession) is True

        req_perm = RequirePermission(permission=PermissionType.CREATE_ENTITY,
                                     target=models.Schema(id=entity.schema_id))
        assert has_permission(user, req_perm, dbsession) is True
        assert has_permission(other_user, req_perm, dbsession) is False
        assert has_permission(testuser, req_perm, dbsession) is True

        su_testgroup = self._create_group(dbsession, BaseGroupSchema(name='su_testgroup', parent_id=None))

        req_perm = RequirePermission(permission=PermissionType.SUPERUSER)

        self._grant_permission(dbsession, PermissionSchema(
                recipient_type=RecipientType.GROUP, recipient_name="su_testgroup",
                permission=PermissionType.SUPERUSER
            ))
        
        add_members(su_testgroup.id, [other_user.id], dbsession)

        assert has_permission(other_user, req_perm, dbsession) is True

    def test_revoke_permission(self, dbsession: Session):
        user, group, parent_group = self._create_user_group_with_perm(dbsession)
        perms = sorted(get_permissions(dbsession, RecipientType.USER, user.id), key=lambda x: x.id)
        result = revoke_permissions([perms[-1].id], dbsession)
        assert result is True

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.USER,
                                recipient_id=user.id)
        assert len(perms) == 3

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.GROUP,
                                recipient_id=group.id)
        assert len(perms) == 2

        perms = get_permissions(db=dbsession, recipient_type=RecipientType.GROUP,
                                recipient_id=parent_group.id)
        assert len(perms) == 1

    def test_revoke_permission__not_existent(self, dbsession: Session):
        self._create_user_group_with_perm(dbsession)
        result = revoke_permissions([9999], dbsession)
        assert result is False
        assert dbsession.query(Permission.id).count() == 5

    @pytest.mark.parametrize(["recipient_type", "attr_name"], [
        (RecipientType.USER.name, 'user'),
        (RecipientType.GROUP.name, 'group'),
    ])
    def test_cascade_delete_permissions(self, dbsession: Session, recipient_type, attr_name):
        user, group, _ = self._create_user_group_with_perm(dbsession)

        permissions_count = (
            dbsession.query(Permission)
            .filter_by(recipient_type=recipient_type, recipient_id=locals().get(attr_name).id)
            .count()
        )
        assert permissions_count > 0

        dbsession.delete(locals().get(attr_name))
        dbsession.commit()

        permissions_count = (
            dbsession.query(Permission)
            .filter_by(recipient_type=recipient_type, recipient_id=locals().get(attr_name).id)
            .count()
        )
        assert permissions_count == 0

        x = 1
