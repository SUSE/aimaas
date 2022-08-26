import typing
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from ..auth.models import User
from ..crud import get_entity_by_id, get_entity
from ..exceptions import MissingEntityUpdateRequestException, AttributeNotDefinedException, \
    MissingEntityCreateRequestException, NoOpChangeException
from ..models import Attribute, AttrType, Entity
from ..traceability.entity import entity_change_details, \
    create_entity_update_request, apply_entity_update_request, create_entity_delete_request, \
    apply_entity_delete_request, create_entity_create_request, apply_entity_create_request
from ..traceability.enum import EditableObjectType, ChangeType, ContentType, ChangeStatus
from ..traceability.models import ChangeRequest, Change, ChangeAttrType, ChangeValueInt, \
    ChangeValueStr

from .mixins import DefaultMixin


class TestUpdateEntityTraceability(DefaultMixin):
    default_data = {
            'slug': 'test',
            'nickname': None,
            'born': datetime(1983, 10, 31, tzinfo=timezone.utc),
            'friends': None,
        }

    def _default_friends(self, dbsession: Session) -> typing.List[int]:
        return sorted(e.id for e in self.get_default_entities(dbsession).values())

    def _create_request(self, dbsession: Session, testuser: User,
                        data: typing.Optional[dict] = None) -> ChangeRequest:
        _data = (data or self.default_data).copy()
        if data is None:
            _data["friends"] = self._default_friends(dbsession)
        entity = self.get_default_entity(dbsession)
        return create_entity_update_request(dbsession, entity.id,
                                            entity.schema_id, _data, testuser)

    def test_create_request(self, dbsession: Session, testuser: User):
        change_request = self._create_request(dbsession, testuser)
        entity = change_request.entity

        assert change_request.created_by == testuser
        assert change_request.created_at is not None
        assert change_request.status == ChangeStatus.PENDING
        assert change_request.reviewed_by is None
        assert change_request.reviewed_at is None
        assert change_request.object_type == EditableObjectType.ENTITY
        assert change_request.object_id == entity.id
        assert change_request.change_type == ChangeType.UPDATE

        schema = self.get_default_schema(dbsession)
        old_data = {key: value
                    for key, value in get_entity(db=dbsession, id_or_slug=entity.id,
                                                 schema=schema).items()
                    if key in self.default_data}
        details = entity_change_details(db=dbsession, change_request_id=change_request.id)

        data = self.default_data.copy()
        data["friends"] = self._default_friends(dbsession)
        assert data == {key: value.new for key, value in details.changes.items()}
        assert old_data == {key: value.old for key, value in details.changes.items()}
        assert old_data == {key: value.current for key, value in details.changes.items()}

    def test_apply_request(self, dbsession: Session, testuser: User):
        change_request = self._create_request(dbsession, testuser)
        apply_entity_update_request(dbsession, change_request=change_request, reviewed_by=testuser,
                                    comment='Autosubmit')

        assert change_request.status == ChangeStatus.APPROVED
        assert change_request.reviewed_at >= change_request.created_at
        assert change_request.reviewed_by == testuser
        assert change_request.comment == 'Autosubmit'

        entity = change_request.entity
        schema = entity.schema
        entity_data = get_entity(db=dbsession, id_or_slug=entity.slug, schema=schema)

        assert entity_data == {
            'id': entity.id,
            'slug': 'test',
            'deleted': False,
            'name': 'Jack',
            'age': 10,
            'born': datetime(1983, 10, 31, tzinfo=timezone.utc),
            'friends': self._default_friends(dbsession),
            'nickname': None,
            'fav_color': ['blue', 'red']
        }

    def test_create__raise_on_missing_change(self, dbsession: Session, testuser: User):
        schema = self.get_default_schema(dbsession)
        entity = get_entity(dbsession, self._default_entity_slug, schema)

        with pytest.raises(NoOpChangeException):
            create_entity_update_request(
                db=dbsession, id_or_slug=entity["slug"], schema_id=schema.id,
                created_by=testuser, data={
                    "age": entity["age"],
                    "born": entity["born"],
                    "slug": entity["slug"]
                }
            )

    def test_apply__raise_on_missing_change(self, dbsession: Session, testuser: User):
        schema_change = ChangeRequest(
            created_by=testuser,
            created_at=datetime.now(timezone.utc),
            object_type=EditableObjectType.SCHEMA,
            object_id=1,
            change_type=ChangeType.UPDATE
        )
        dbsession.add(schema_change)
        dbsession.flush()

        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request=schema_change,
                                        reviewed_by=testuser)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, testuser: User):
        entity = self.get_default_entity(dbsession)
        r = ChangeRequest(
            created_by=testuser,
            created_at=datetime.now(timezone.utc),
            object_type=EditableObjectType.ENTITY,
            object_id=entity.id,
            change_type=ChangeType.UPDATE
        )
        name_val = ChangeValueStr(new_value='test', old_value="Jack")
        attr_val = ChangeValueStr(new_value='test')
        dbsession.add_all([name_val, attr_val])
        dbsession.flush()

        name = Change(
            change_request=r, value_id=name_val.id, field_name='name', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=entity.id
        )

        a = Attribute(name='test', type=AttrType.STR)
        attr = Change(
            change_request=r, value_id=attr_val.id, attribute=a, 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE,
            object_id=entity.id
        )
        dbsession.add_all([r, name, a, attr])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_update_request(db=dbsession, change_request=r, reviewed_by=testuser)

    def test_list_change(self, dbsession: Session, testuser: User):
        entity = self.get_default_entities(dbsession)["Jane"]
        change_request = create_entity_update_request(dbsession, entity.id, entity.schema_id,
                                                      {"friends": self._default_friends(dbsession)},
                                                      testuser)

        details = entity_change_details(dbsession, change_request_id=change_request.id)
        friends = self._default_friends(dbsession)
        assert details.changes["friends"].dict() == {
            'new': friends,
            'old': friends[:1],
            'current': friends[:1]}

        apply_entity_update_request(dbsession, change_request=change_request, reviewed_by=testuser,
                                    comment="Test")


class TestDeleteEntityTraceability(DefaultMixin):
    def _create_request(self, dbsession: Session, testuser: User) -> ChangeRequest:
        entity = self.get_default_entity(dbsession)
        return create_entity_delete_request(dbsession, id_or_slug=entity.slug,
                                            schema_id=entity.schema_id, created_by=testuser)

    def test_create_request(self, dbsession: Session, testuser: User):
        entity = self.get_default_entity(dbsession)
        change_request = self._create_request(dbsession, testuser)

        assert change_request.created_by == testuser
        assert change_request.created_at is not None
        assert change_request.status == ChangeStatus.PENDING
        assert change_request.reviewed_by is None
        assert change_request.reviewed_at is None
        assert change_request.object_type == EditableObjectType.ENTITY
        assert change_request.object_id == entity.id
        assert change_request.change_type == ChangeType.DELETE

        changes = entity_change_details(db=dbsession, change_request_id=change_request.id)

        assert changes.changes["deleted"].dict() == {'new': True, 'old': False, 'current': False}

    def test_apply_request(self, dbsession: Session, testuser: User):
        change_request = self._create_request(dbsession, testuser)
        apply_entity_delete_request(dbsession, change_request=change_request, reviewed_by=testuser,
                                    comment='test')

        assert change_request.reviewed_by == testuser
        assert change_request.reviewed_at >= change_request.created_at
        assert change_request.status == ChangeStatus.APPROVED
        assert change_request.comment == "test"

        entity = self.get_default_entity(dbsession)
        assert entity.deleted

    def test_raise_on_missing_change(self, dbsession: Session, testuser: User):
        entity = self.get_default_entity(dbsession)
        schema_change = ChangeRequest(
            created_by=testuser,
            created_at=datetime.now(timezone.utc),
            object_type=EditableObjectType.SCHEMA,
            object_id=entity.id,
            change_type=ChangeType.DELETE
        )
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityUpdateRequestException):
            apply_entity_update_request(db=dbsession, change_request=schema_change,
                                        reviewed_by=testuser, comment=None)


class TestCreateEntityTraceability(DefaultMixin):
    default_data = {
            'name': 'John',
            'slug': 'John',
            'nickname': 'john',
            'age': 10,
            'friends': None,
            'born': datetime(1990, 6, 30, tzinfo=timezone.utc)
        }

    def _default_friends(self, dbsession: Session) -> typing.List[int]:
        return [self.get_default_entities(dbsession)["Jack"].id]

    def _create_request(self, dbsession: Session, user: User, data: typing.Optional[dict] = None) \
            -> ChangeRequest:
        _data = (data or self.default_data).copy()
        if data is None:
            _data["friends"] = self._default_friends(dbsession)
        schema = self.get_default_schema(dbsession)
        return create_entity_create_request(db=dbsession, data=_data, schema_id=schema.id,
                                            created_by=user)

    def test_create_request(self, dbsession: Session, testuser: User):
        start_time = datetime.now(timezone.utc)
        change_request = self._create_request(dbsession=dbsession, user=testuser)

        assert 0 == dbsession.query(Entity.id).filter(Entity.slug == "John").count()

        assert change_request.created_by == testuser
        assert change_request.created_at.astimezone(timezone.utc) >= start_time
        assert change_request.status == ChangeStatus.PENDING
        assert change_request.reviewed_by is None
        assert change_request.reviewed_at is None
        assert change_request.object_type == EditableObjectType.ENTITY
        assert change_request.object_id is None
        assert change_request.change_type == ChangeType.CREATE

        changes = dbsession.query(Change).filter(Change.change_request_id == change_request.id)
        assert 7 == changes.count()
        changed_values = {}
        schema = self.get_default_schema(dbsession)
        data = self.default_data.copy()
        data["friends"] = self._default_friends(dbsession)
        for c in changes:
            key = c.field_name or c.attribute.name
            Model = c.data_type.value.model
            value = dbsession.query(Model).filter(Model.id == c.value_id).one()
            assert value.old_value is None
            if isinstance(value.new_value, datetime):
                changed_values[key] = value.new_value.astimezone(timezone.utc)
            elif key == "schema_id":
                assert schema.id == value.new_value
            elif isinstance(data.get(key, None), list):
                if key not in changed_values:
                    changed_values[key] = []
                changed_values[key].append(value.new_value)
            else:
                changed_values[key] = value.new_value

        assert data == changed_values

    def test_approve_request(self, dbsession: Session, testuser: User):
        change_request = self._create_request(dbsession=dbsession, user=testuser)
        start_time = datetime.now(timezone.utc)
        apply_entity_create_request(db=dbsession, change_request=change_request,
                                    reviewed_by=testuser, comment='Looks good to me 👌')

        dbsession.refresh(change_request)
        assert change_request.status == ChangeStatus.APPROVED
        assert change_request.reviewed_by == testuser
        assert change_request.created_at.astimezone(timezone.utc) <= start_time
        assert start_time <= change_request.reviewed_at.astimezone(timezone.utc)
        assert change_request.object_id is not None

        changes = dbsession.query(Change).filter(Change.change_request_id == change_request.id)
        assert 7 == changes.count()
        assert 0 == changes.filter(Change.object_id == None).count()

        entity = get_entity_by_id(db=dbsession, entity_id=change_request.object_id)
        assert entity.name == self.default_data["name"]
        assert entity.slug == self.default_data["slug"]
    
    def test_raise_on_missing_change(self, dbsession: Session, testuser: User):
        schema_change = ChangeRequest(
            created_by=testuser,
            created_at=datetime.utcnow(),
            object_type=EditableObjectType.SCHEMA,
            change_type=ChangeType.CREATE
        )
        dbsession.add(schema_change)
        dbsession.flush()
        
        # raise on wrong change
        with pytest.raises(MissingEntityCreateRequestException):
            apply_entity_create_request(db=dbsession, change_request=schema_change,
                                        reviewed_by=testuser)
        dbsession.rollback()
        # raise on nonexistent change
        with pytest.raises(MissingEntityCreateRequestException):
            fake = ChangeRequest(id=42)
            apply_entity_create_request(db=dbsession, change_request=fake, reviewed_by=testuser)

    def test_raise_on_attribute_not_defined(self, dbsession: Session, testuser: User):
        r = ChangeRequest(
            created_by=testuser,
            created_at=datetime.now(timezone.utc),
            object_type=EditableObjectType.ENTITY,
            change_type=ChangeType.CREATE
        )
        schema = self.get_default_schema(dbsession)
        name_val = ChangeValueStr(new_value='test')
        slug_val = ChangeValueStr(new_value='test')
        schema_val = ChangeValueInt(new_value=schema.id)
        attr_val = ChangeValueStr(new_value='test')
        dbsession.add_all([name_val, slug_val, schema_val, attr_val])
        dbsession.flush()

        name = Change(
            change_request=r, value_id=name_val.id, field_name='name', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        slug = Change(
            change_request=r, value_id=slug_val.id, field_name='slug', 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        schema = Change(
            change_request=r, value_id=schema_val.id, field_name='schema_id', 
            data_type=ChangeAttrType.INT, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )

        a = Attribute(name='test', type=AttrType.STR)
        attr = Change(
            change_request=r, value_id=attr_val.id, attribute=a, 
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.CREATE
        )
        dbsession.add_all([r, name, slug, schema, a, attr])
        dbsession.flush()

        with pytest.raises(AttributeNotDefinedException):
            apply_entity_create_request(db=dbsession, change_request=r, reviewed_by=testuser)

    def test_get_entity_create_details(self, dbsession: Session, testuser: User):
        data = {
            "name": "Jackson",
            "slug": "jackson",
            "fav_color": ["cyan", "violet"],
            "age": 42,
            "friends": self._default_friends(dbsession)
        }
        change_request = self._create_request(dbsession=dbsession, user=testuser, data=data)

        change = entity_change_details(db=dbsession, change_request_id=change_request.id)
        assert all(value.old is None
                   for key, value in change.changes.items()
                   if key != "schema_id" and not isinstance(data[key], list))
        assert all(value.old == []
                   for key, value in change.changes.items()
                   if key != "schema_id" and isinstance(data[key], list))
        assert all(value.current is None
                   for key, value in change.changes.items()
                   if key not in ["name", "slug", "schema_id"] and not isinstance(data[key], list))
        assert all(value.current == []
                   for key, value in change.changes.items()
                   if isinstance(data.get(key, None), list))
        new_values = {key: value.new for key, value in change.changes.items() if key != "schema_id"}
        assert new_values == data
