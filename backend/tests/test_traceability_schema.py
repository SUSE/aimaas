import typing

from fastapi_pagination import Params
from sqlalchemy.orm import Session

from ..auth.models import User
from ..models import Schema
from ..schemas.schema import AttrDefSchema, SchemaCreateSchema, SchemaUpdateSchema
from ..schemas.traceability import ChangeSchema
from ..traceability.enum import ChangeType, ChangeStatus, EditableObjectType
from ..traceability.models import ChangeRequest, Change
from ..traceability.schema import get_recent_schema_changes, schema_change_details, \
    create_schema_create_request, apply_schema_create_request, \
    create_schema_update_request, apply_schema_update_request, create_schema_delete_request, \
    apply_schema_delete_request

from .mixins import DefaultMixin


class TestGetChanges(DefaultMixin):
    def test_get_recent_schema_changes(self, dbsession: Session):
        schema = self.get_default_schema(dbsession)
        page = get_recent_schema_changes(db=dbsession, schema_id=schema.id,
                                         params=Params(size=20, page=1))
        assert len(page.items) == 11
        assert sum(1 for i in page.items
                   if i.status == ChangeStatus.PENDING
                   and i.object_type == EditableObjectType.ENTITY) == 1


class TestCreateSchema(DefaultMixin):
    default_data = {
        "name": "Car",
        "slug": "car",
        "attributes": None
    }

    def _default_attributes(self, dbsession: Session) -> typing.List[AttrDefSchema]:
        attrs = [
            AttrDefSchema(
                name='color',
                type='STR',
                required=False,
                unique=False,
                list=False,
                key=False,
                description='Color of this car'
            ),
            AttrDefSchema(
                name='max_speed',
                type='INT',
                required=True,
                unique=False,
                list=False,
                key=False
            ),
            AttrDefSchema(
                name="release_year",
                type='DT',
                required=False,
                unique=False,
                list=False,
                key=False
            ),
            AttrDefSchema(
                name="extras",
                type="STR",
                required=False,
                unique=False,
                list=True,
                key=False,
                description='Special extras of car'
            )
        ]

        person = self.get_default_schema(dbsession)
        owner = AttrDefSchema(
                name='owner',
                type='FK',
                required=True,
                unique=False,
                list=False,
                key=False,
                bound_schema_id=person.id
            )
        attrs.append(owner)
        return attrs

    def create_request(self, dbsession: Session, testuser: User) -> ChangeRequest:
        data = self.default_data.copy()
        data["attributes"] = self._default_attributes(dbsession)
        return create_schema_create_request(dbsession, SchemaCreateSchema(**data),
                                            testuser)

    def test_create_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)

        assert change_request.id is not None
        assert change_request.created_by == testuser
        assert change_request.created_at is not None
        assert change_request.status == ChangeStatus.PENDING
        assert change_request.object_id is None

        changes = schema_change_details(db=dbsession, change_request_id=change_request.id)
        person = self.get_default_schema(dbsession)
        expected_schema_new = {
            'name': 'Car',
            'slug': 'car',
            'reviewable': False,
            'color.required': False,
            'color.unique': False,
            'color.list': False,
            'color.key': False,
            'color.description': 'Color of this car',
            'color.bound_schema_id': None,
            'color.name': 'color',
            'color.type': 'STR',
            'max_speed.required': True,
            'max_speed.unique': False,
            'max_speed.list': False,
            'max_speed.key':  False,
            'max_speed.description': None,
            'max_speed.bound_schema_id': None,
            'max_speed.name': 'max_speed',
            'max_speed.type': 'INT',
            'release_year.required': False,
            'release_year.unique': False,
            'release_year.list': False,
            'release_year.key': False,
            'release_year.description': None,
            'release_year.bound_schema_id': None,
            'release_year.name': 'release_year',
            'release_year.type': 'DT',
            'owner.required': True,
            'owner.unique': False,
            'owner.list': False,
            'owner.key': False,
            'owner.description': None,
            'owner.bound_schema_id': person.id,
            'owner.name': 'owner',
            'owner.type': 'FK',
            'extras.required': False,
            'extras.unique': False,
            'extras.list': True,
            'extras.key': False,
            'extras.description': 'Special extras of car',
            'extras.bound_schema_id': None,
            'extras.name': 'extras',
            'extras.type': 'STR',
        }
        assert expected_schema_new == {key: value.new for key, value in changes.changes.items()}
        assert all(v.old is None for v in changes.changes.values())
        assert all(v.current is None for v in changes.changes.values())

    def test_appy_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)
        apply_schema_create_request(db=dbsession, change_request=change_request,
                                    reviewed_by=testuser, comment='test')
        assert change_request.comment == "test"
        assert change_request.reviewed_by == testuser
        assert change_request.status == ChangeStatus.APPROVED
        assert change_request.reviewed_at >= change_request.created_at


class TestUpdateSchema(DefaultMixin):
    default_data = {
        "slug": "test",
        "reviewable": True,
        "attributes": None
    }

    def _default_attributes(self, dbsession: Session) -> typing.List[AttrDefSchema]:
        attr_defs = {a.name: a for a in self.get_default_attr_def_schemas(dbsession)}
        new_changed = [
            AttrDefSchema(
                name='address2',
                type='FK',
                required=True,
                unique=False,
                list=True,
                key=True,
                bound_schema_id=-1
            ),
        ]
        attr_defs["age"].required = False
        attr_defs["age"].key = False
        new_changed.append(attr_defs["age"])
        return new_changed + [a for a in attr_defs.values() if a.name in ('friends', 'nickname', 'fav_color')]

    def create_request(self, dbsession: Session, testuser: User) -> ChangeRequest:
        data = self.default_data.copy()
        data["attributes"] = self._default_attributes(dbsession)
        return create_schema_update_request(db=dbsession, id_or_slug='person', created_by=testuser,
                                            data=SchemaUpdateSchema(**data))

    def test_create_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)
        assert change_request.created_by is not None
        assert change_request.created_at is not None
        assert change_request.status == ChangeStatus.PENDING

        details = schema_change_details(db=dbsession, change_request_id=change_request.id)
        assert details.change_type == ChangeType.UPDATE
        assert details.created_at is not None
        assert details.created_by == testuser.username
        assert details.reviewed_at is None
        assert details.reviewed_by is None
        assert details.comment is None
        assert details.status == ChangeStatus.PENDING
        assert details.schema_.name == 'Person' and details.schema_.slug == 'person'

        expected = {
            'slug': ChangeSchema(new='test', old='person', current='person'),
            'reviewable': ChangeSchema(new=True, old=False, current=False),
            'age.key': ChangeSchema(new=False, old=True, current=True),
            'age.required': ChangeSchema(new=False, old=True, current=True),
            'born': ChangeSchema(new=None, old='born', current='born'),
            'address2.unique': ChangeSchema(new=False, old=None, current=None),
            'address2.list': ChangeSchema(new=True, old=None, current=None),
            'address2.key': ChangeSchema(new=True, old=None, current=None),
            'address2.description': ChangeSchema(new=None, old=None, current=None),
            'address2.bound_schema_id': ChangeSchema(new=-1, old=None, current=None),
            'address2.name': ChangeSchema(new='address2', old=None, current=None),
            'address2.type': ChangeSchema(new='FK', old=None, current=None),
            'address2.required': ChangeSchema(new=True, old=None, current=None)
        }
        assert expected == details.changes

        changes = {c.field_name or c.attribute.name: c.change_type
                   for c in dbsession.query(Change)
                       .filter(Change.change_request_id == change_request.id)}
        assert changes == {
            'name': ChangeType.UPDATE, 'slug': ChangeType.UPDATE, 'reviewable': ChangeType.UPDATE,
            'age.required': ChangeType.UPDATE, 'age.key': ChangeType.UPDATE,
            'address2.name': ChangeType.CREATE,
            'address2.type': ChangeType.CREATE, 'address2.required': ChangeType.CREATE,
            'address2.unique': ChangeType.CREATE, 'address2.list': ChangeType.CREATE,
            'address2.key': ChangeType.CREATE, 'address2.description': ChangeType.CREATE,
            'address2.bound_schema_id': ChangeType.CREATE, 'born': ChangeType.DELETE
        }

    def test_apply_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)
        apply_schema_update_request(db=dbsession, change_request=change_request,
                                    reviewed_by=testuser, comment='test')

        assert change_request.reviewed_at >= change_request.created_at
        assert change_request.reviewed_by == testuser
        assert change_request.comment == "test"
        assert change_request.status == ChangeStatus.APPROVED

        schema = dbsession.query(Schema).filter(Schema.id == change_request.object_id).one()
        attr_names = {d.attribute.name for d in schema.attr_defs}
        assert "born" not in attr_names
        assert "address2" in attr_names

        details = schema_change_details(db=dbsession, change_request_id=change_request.id)
        expected = {
            'slug': ChangeSchema(new='test', old='person', current='test'),
            'reviewable': ChangeSchema(new=True, old=False, current=True),
            'age.key': ChangeSchema(new=False, old=True, current=False),
            'age.required': ChangeSchema(new=False, old=True, current=False),
            'born': ChangeSchema(new=None, old='born', current=None),
            'address2.unique': ChangeSchema(new=False, old=None, current=False),
            'address2.list': ChangeSchema(new=True, old=None, current=True),
            'address2.key': ChangeSchema(new=True, old=None, current=True),
            'address2.description': ChangeSchema(new=None, old=None, current=None),
            'address2.bound_schema_id': ChangeSchema(new=-1, old=None, current=schema.id),
            'address2.name': ChangeSchema(new='address2', old=None, current='address2'),
            'address2.type': ChangeSchema(new='FK', old=None, current='FK'),
            'address2.required': ChangeSchema(new=True, old=None, current=True)
        }
        assert expected == details.changes


class TestDeleteSchema:
    def create_request(self, dbsession: Session, testuser: User) -> ChangeRequest:
        return create_schema_delete_request(db=dbsession, id_or_slug='person', created_by=testuser)

    def test_create_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)
        assert change_request.status == ChangeStatus.PENDING
        assert change_request.created_at is not None
        assert change_request.created_by == testuser

        details = schema_change_details(db=dbsession, change_request_id=change_request.id)
        assert details.change_type == ChangeType.DELETE
        assert details.created_at is not None
        assert details.created_by == testuser.username
        assert details.reviewed_at is None
        assert details.reviewed_by is None
        assert details.comment is None
        assert details.status == ChangeStatus.PENDING
        assert details.schema_.name == 'Person' and details.schema_.slug == 'person'
        assert details.changes == {"deleted": ChangeSchema(new=True, old=False, current=False)}

    def test_apply_request(self, dbsession: Session, testuser: User):
        change_request = self.create_request(dbsession=dbsession, testuser=testuser)
        apply_schema_delete_request(db=dbsession, change_request=change_request,
                                    reviewed_by=testuser, comment='test')

        assert change_request.reviewed_at >= change_request.created_at
        assert change_request.reviewed_by == testuser
        assert change_request.status == ChangeStatus.APPROVED
        assert change_request.comment == "test"

        details = schema_change_details(db=dbsession, change_request_id=change_request.id)
        assert details.change_type == ChangeType.DELETE
        assert details.created_at is not None
        assert details.created_by == testuser.username
        assert details.reviewed_at is not None
        assert details.reviewed_by == testuser.username
        assert details.comment == "test"
        assert details.status == ChangeStatus.APPROVED
        assert details.schema_.name == 'Person' and details.schema_.slug == 'person'
        assert details.changes == {"deleted": ChangeSchema(new=True, old=False, current=True)}
