import typing

from sqlalchemy.orm import Session

from ..auth.crud import create_group, create_user, add_members, grant_permission
from ..auth.enum import RecipientType, PermissionTargetType, PermissionType
from ..auth.models import User, Group
from ..models import Schema, AttributeDefinition, Entity
from ..schemas.auth import BaseGroupSchema, UserCreateSchema, PermissionSchema
from ..schemas.schema import AttrDefSchema


class DefaultMixin:
    _default_entity_slug = "Jack"
    _default_schema_slug = "person"

    def get_default_schema(self, db: Session) -> Schema:
        return db.query(Schema).filter(Schema.slug == self._default_schema_slug).one()

    def get_default_entities(self, db: Session) -> typing.Dict[str, Entity]:
        return {e.slug: e
                for e in db.query(Entity).join(Schema)
                .filter(Schema.slug == self._default_schema_slug).all()}

    def get_default_entity(self, db: Session) -> Entity:
        return db.query(Entity)\
            .join(Schema)\
            .filter(Schema.slug == self._default_schema_slug,
                    Entity.slug == self._default_entity_slug)\
            .one()

    def get_default_attr_defs(self, db: Session) -> typing.List[AttributeDefinition]:
        return db.query(AttributeDefinition)\
            .join(Schema, Schema.id == AttributeDefinition.schema_id)\
            .filter(Schema.slug == self._default_schema_slug)\
            .all()

    def get_default_attr_def_schemas(self, db: Session) -> typing.List[AttrDefSchema]:
        return [AttrDefSchema.from_orm(a) for a in self.get_default_attr_defs(db)]

    def get_default_attr_def_dicts(self, db: Session) -> typing.List[dict]:
        d = []
        for a in self.get_default_attr_def_schemas(db):
            ad = a.dict()
            ad["type"] = ad["type"].name
            d.append(ad)
        return d

    @staticmethod
    def strip_ids(data: dict) -> dict:
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict. Got instead: {data} ({type(data)})")
        return {key: value for key, value in data.items() if key != "id"}


class CreateMixin(DefaultMixin):
    default_username = "testuser-0"
    default_password = "secret"
    default_groupname = "test"

    def _create_group(self, dbsession: Session, data: typing.Optional[BaseGroupSchema] = None) \
            -> Group:
        data = data or BaseGroupSchema(name=self.default_groupname, parent_id=None)
        return create_group(db=dbsession, data=data)

    def _create_user(self, dbsession: Session, data: typing.Optional[UserCreateSchema] = None) \
            -> User:
        data = data or UserCreateSchema(username=self.default_username,
                                        password=self.default_password,
                                        email="t@example.org")
        return create_user(dbsession, data)

    def _grant_permission(self, dbsession: Session, data: typing.Optional[PermissionSchema] = None)\
            -> bool:
        if not data:
            user = self._create_user(dbsession)
            entity = self.get_default_entity(dbsession)
            data = PermissionSchema(recipient_type=RecipientType.USER, recipient_name=user.username,
                                    obj_type=PermissionTargetType.ENTITY, obj_id=entity.id,
                                    permission=PermissionType.UPDATE_ENTITY)
        return grant_permission(data, dbsession)

    def _create_user_group_with_perm(self, dbsession: Session) -> typing.Tuple[User, Group, Group]:
        pgroup = self._create_group(dbsession)
        group = self._create_group(dbsession, BaseGroupSchema(name="subgroup", parent_id=pgroup.id))
        user = self._create_user(dbsession)
        add_members(group.id, [user.id], dbsession)
        entity = self.get_default_entity(dbsession)

        # Grant permission to user
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.USER, recipient_name=user.username,
            obj_type=PermissionTargetType.ENTITY, obj_id=entity.id,
            permission=PermissionType.DELETE_ENTITY))

        # Grant permission to parent group
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.GROUP, recipient_name=pgroup.name,
            obj_type=PermissionTargetType.SCHEMA, obj_id=entity.id,
            permission=PermissionType.READ_ENTITY))

        # Grant permission to group
        self._grant_permission(dbsession, PermissionSchema(
            recipient_type=RecipientType.GROUP, recipient_name=group.name,
            obj_type=PermissionTargetType.SCHEMA, obj_id=entity.schema_id,
            permission=PermissionType.UPDATE_ENTITY))

        return user, group, pgroup
