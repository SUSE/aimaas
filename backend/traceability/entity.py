from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from itertools import zip_longest, groupby
from typing import List, Tuple, Optional, Dict, Any, Union

from fastapi_pagination import Params, Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from .. import crud
from ..auth.models import User
from ..config import DEFAULT_PARAMS
from ..enum import ModelVariant
from ..exceptions import MissingChangeException, MissingEntityCreateRequestException, \
    AttributeNotDefinedException, MissingEntityUpdateRequestException, \
    MissingEntityDeleteRequestException, MissingChangeRequestException
from ..models import Entity, AttributeDefinition, Schema, Attribute
from ..schemas.entity import EntityModelFactory
from ..schemas.traceability import EntityChangeDetailSchema

from .enum import EditableObjectType, ContentType, ChangeType, ChangeStatus
from .models import ChangeRequest, Change, ChangeAttrType, ChangeValueInt, ChangeValueBool, \
    ChangeValueStr


def get_recent_entity_changes(db: Session, entity_id: int, params: Params = DEFAULT_PARAMS) \
        -> Page[ChangeRequest]:
    q = db.query(ChangeRequest)\
        .filter(ChangeRequest.object_id == entity_id,
                ChangeRequest.object_type == EditableObjectType.ENTITY)\
        .order_by(ChangeRequest.created_at.desc())
    return paginate(q, params)


def _fill_in_change_request_info(change: dict, change_request: ChangeRequest, entity: Entity):
    change['object_type'] = change_request.object_type.name
    change['change_type'] = change_request.change_type.name
    change['reviewed_at'] = change_request.reviewed_at
    change['created_at'] = change_request.created_at
    change['status'] = change_request.status
    change['comment'] = change_request.comment
    change['created_by'] = change_request.created_by.username
    change['reviewed_by'] = change_request.reviewed_by.username if change_request.reviewed_by else None
    change['entity'] = {'slug': entity.slug, 'name': entity.name, 'schema': entity.schema.slug}


def _fill_in_entity_change(change: dict, entity_change: Change, entity: Entity, db: Session):
    field = entity_change.field_name
    ValueModel = entity_change.data_type.value.model
    v = db.execute(select(ValueModel).where(ValueModel.id == entity_change.value_id)).scalar()
    change['changes'][field] = {'new': v.new_value,
                                'old': v.old_value,
                                'current': getattr(entity, field, None) if entity.id else None}


def _fill_in_field_change(change: dict, entity_change: Change, entity: Entity,
                          listed_changes: dict[int, List[Change]], checked_listed: List[int],
                          db: Session):
    attr = entity_change.attribute
    ValueModel = entity_change.data_type.value.model
    if attr.id not in listed_changes:
        v = db.execute(select(ValueModel).where(ValueModel.id == entity_change.value_id)).scalar()
        try:
            current = get_old_value(db, entity, attr.name)
        except KeyError:
            current = None
        change['changes'][attr.name] = {'new': v.new_value, 'old': v.old_value, 'current': current}
        return
    
    if attr.id in checked_listed:
        return
    checked_listed.append(attr.id)
    changes = listed_changes[attr.id]
    values = db.execute(select(ValueModel).where(ValueModel.id.in_([i.value_id for i in changes]))).scalars().all()
    values = [i.new_value for i in values if i.new_value is not None]
    change['changes'][attr.name] = {'new': values,
                                    'old': [] if attr.id in listed_changes else None,
                                    'current': [] if attr.id in listed_changes else None}


def entity_change_details(db: Session, change_request_id: int) -> EntityChangeDetailSchema:
    try:
        change_request = db.query(ChangeRequest)\
            .filter(ChangeRequest.id == change_request_id,
                    ChangeRequest.object_type == EditableObjectType.ENTITY).one()
    except NoResultFound:
        raise MissingChangeRequestException(obj_id=change_request_id)

    changes_query = (select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ENTITY))

    entity_changes = db.execute(changes_query.where(Change.field_name != None)).scalars().all()
    fields_changes = db.execute(changes_query.where(Change.attribute_id != None)).scalars().all()
    if not entity_changes and not fields_changes:
        raise MissingChangeException(obj_id=change_request_id)
    
    # WARNING: technically, these changes within one ChangeRequest can reference different entities
    # although, they should not
    if change_request.change_type == ChangeType.CREATE and change_request.status != ChangeStatus.APPROVED:
        entity = Entity(name='', slug='', deleted=None)
        schema_change = db.execute(
            changes_query
            .where(Change.change_type == ChangeType.CREATE)
            .where(Change.field_name == 'schema_id')
            .where(Change.data_type == ChangeAttrType.INT)
        ).scalar()
        schema_id = db.execute(select(ChangeValueInt).where(ChangeValueInt.id == schema_change.value_id)).scalar()
        schema = crud.get_schema(db=db, id_or_slug=schema_id.new_value)
        entity.schema = schema
        entity.schema_id = schema_id.new_value
    else:
        entity = crud.get_entity_by_id(db=db, entity_id=change_request.object_id)
    change_ = {'changes': {}}
    _fill_in_change_request_info(change=change_, change_request=change_request, entity=entity)

    deleted = [i for i in entity_changes if i.field_name == 'deleted']
    if deleted:
        deleted = deleted[0]
        v = db.execute(select(ChangeValueBool).where(ChangeValueBool.id == deleted.value_id)).scalar()
        change_['changes']['deleted'] = {'new': v.new_value, 'old': v.old_value, 'current': entity.deleted}
        return EntityChangeDetailSchema(**change_)

    for change in entity_changes:
        _fill_in_entity_change(change=change_, entity_change=change, entity=entity, db=db)

    attr_defs = {attr_def.attribute_id: attr_def for attr_def in entity.schema.attr_defs}
    for attr_id, changes in groupby(fields_changes, key=lambda x: x.attribute_id):
        _changes = list(changes)
        ValueModel = _changes[0].data_type.value.model
        attr_name = attr_defs[attr_id].attribute.name
        if attr_defs[attr_id].list:
            values = db.query(ValueModel).filter(ValueModel.id.in_([c.value_id for c in _changes]))
            change_["changes"][attr_name] = {
                "new": sorted(v.new_value for v in values if v.new_value),
                "old": sorted(v.old_value for v in values if v.old_value),
                "current": get_old_value(db, entity, attr_name)
            }
        else:
            value = db.query(ValueModel).filter(ValueModel.id == _changes[0].value_id).one()
            current = get_old_value(db, entity, attr_name)
            change_["changes"][attr_name] = {"new": value.new_value, "old": value.old_value,
                                             "current": current[0] if current else None}
    return EntityChangeDetailSchema(**change_)


def get_old_value(db: Session, entity: Entity, attr_name: str) -> List[Any]:
    val = entity.get(attr_name, db)
    if isinstance(val, list):
        return [v.value for v in val]
    return [val.value] if val is not None else []


def _create_value_changes(db: Session, change_request: ChangeRequest, schema: Schema, data: dict,
                          entity: Optional[Entity] = None, new: bool = False):
    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in schema.attr_defs}
    for field, value in data.items():
        attr_def = attr_defs.get(field)
        attr: Attribute = attr_def.attribute
        model, caster, _ = attr.type.value
        model = ChangeAttrType[attr.type.name].value.model
        new_values = crud._convert_values(attr_def=attr_def, value=value, caster=caster) or []
        old_values = [] if new else get_old_value(db=db, entity=entity, attr_name=attr.name)
        for new_val, old_val in zip_longest(sorted(new_values), sorted(old_values), fillvalue=None):
            v = model(new_value=new_val, old_value=old_val)
            db.add(v)
            db.flush()
            change = Change(
                change_request=change_request,
                value_id=v.id,
                attribute=attr,
                data_type=ChangeAttrType[attr.type.name],
                content_type=ContentType.ENTITY,
                change_type=ChangeType.CREATE if new else ChangeType.UPDATE,
                object_id=None if new else entity.id
            )
            db.add(change)
            db.flush()


def create_entity_create_request(db: Session, data: dict, schema_id: int, created_by: User,
                                 commit: bool = True) -> ChangeRequest:
    crud.create_entity(db=db, schema_id=schema_id, data=deepcopy(data), commit=False)
    db.rollback()
    
    sch: Schema = db.execute(
        select(Schema).where(Schema.id == schema_id).where(Schema.deleted == False)
    ).scalar()

    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.ENTITY,
        change_type=ChangeType.CREATE
    )
    
    entity_change_kwargs = {
        'change_request': change_request,
        'content_type': ContentType.ENTITY,
        'change_type': ChangeType.CREATE
    }

    name_val = ChangeValueStr(new_value=data.pop('name'))
    db.add(name_val)
    db.flush()
    name_change = Change(
        value_id=name_val.id, 
        field_name='name', 
        data_type=ChangeAttrType.STR,
        **entity_change_kwargs
    )

    slug_val = ChangeValueStr(new_value=data.pop('slug'))
    db.add(slug_val)
    db.flush()
    slug_change = Change(
        value_id=slug_val.id, 
        field_name='slug', 
        data_type=ChangeAttrType.STR, 
        **entity_change_kwargs
    )

    schema_val = ChangeValueInt(new_value=schema_id)
    db.add(schema_val)
    db.flush()
    schema_change = Change(
        value_id=schema_val.id, 
        field_name='schema_id', 
        data_type=ChangeAttrType.INT, 
        **entity_change_kwargs
    )

    db.add_all([change_request, name_change, slug_change, schema_change])

    _create_value_changes(db=db, change_request=change_request, schema=sch, data=data, new=True)

    if commit:
        db.commit()
    else:
        db.flush()
    return change_request


def apply_entity_create_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: Optional[str] = None) -> Tuple[bool, Entity]:
    entity_change = (
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    )
    name_change = db.execute(
        entity_change
        .where(Change.field_name == 'name')
        .where(Change.data_type == ChangeAttrType.STR)
    ).scalar()
    slug_change = db.execute(
        entity_change
        .where(Change.field_name == 'slug')
        .where(Change.data_type == ChangeAttrType.STR)
    ).scalar()
    schema_change = db.execute(
        entity_change
        .where(Change.field_name == 'schema_id')
        .where(Change.data_type == ChangeAttrType.INT)
    ).scalar() 
    if not all([name_change, slug_change, schema_change]):
        raise MissingEntityCreateRequestException(obj_id=change_request.id)
    
    schema_id = db.execute(
        select(ChangeValueInt).where(ChangeValueInt.id == schema_change.value_id)
    ).scalar().new_value
    schema = crud.get_schema(db=db, id_or_slug=schema_id)

    name = db.execute(
        select(ChangeValueStr)
        .where(ChangeValueStr.id == name_change.value_id)
    ).scalar().new_value
    slug = db.execute(
        select(ChangeValueStr)
        .where(ChangeValueStr.id == slug_change.value_id)
    ).scalar().new_value

    value_changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.attribute_id != None)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()

    single_changes = []
    listed_changes = defaultdict(list)
    for change in value_changes:
        attr_def = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == schema.id)
            .where(AttributeDefinition.attribute_id == change.attribute_id)
        ).scalar()
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=change.attribute_id, schema_id=schema.id)

        if attr_def.list:
            listed_changes[change.attribute.name].append(change)
        else:
            single_changes.append(change)

    data = {'name': name, 'slug': slug}
    for change in single_changes:
        ChangeValueModel = change.data_type.value.model
        v = db.execute(select(ChangeValueModel).where(ChangeValueModel.id == change.value_id)).scalar()
        data[change.attribute.name] = v.new_value

    for attr_name, changes in listed_changes.items():
        ChangeValueModel = changes[0].data_type.value.model
        value_ids = [i.value_id for i in changes]
        values = db.execute(select(ChangeValueModel).where(ChangeValueModel.id.in_(value_ids))).scalars().all()
        data[attr_name] = [i.new_value for i in values if i.new_value is not None]

    factory = EntityModelFactory()
    EntityCreateModel = factory(schema=schema, variant=ModelVariant.CREATE)

    e = crud.create_entity(
        db=db, 
        schema_id=schema.id, 
        data=EntityCreateModel(**data).dict(),
        commit=False
    )
    name_change.object_id = e.id  # setting object_id is required
    slug_change.object_id = e.id  # to be able to show details
    schema_change.object_id = e.id
    for change in value_changes:  # for this change request
        change.object_id = e.id
    change_request.object_id = e.id
    change_request.status = ChangeStatus.APPROVED
    change_request.reviewed_by = reviewed_by
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.comment = comment
    db.commit()
    return True, e


def create_entity_update_request(
        db: Session, id_or_slug: Union[int, str], schema_id: int, data: dict, created_by: User,
        commit: bool = True) -> ChangeRequest:
    crud.update_entity(db=db, id_or_slug=id_or_slug, schema_id=schema_id, data=deepcopy(data),
                       commit=False)
    db.rollback()
    if isinstance(id_or_slug, int):
        q = select(Entity).where(Entity.id == id_or_slug)
    else:
        q = select(Entity).where(Entity.slug == id_or_slug)
    entity = db.execute(q).scalar()
    
    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.ENTITY,
        object_id=entity.id,
        change_type=ChangeType.UPDATE,
    )
    db.add(change_request)
    
    entity_fields = {'name': data.pop('name', None), 'slug': data.pop('slug', None)}
    entity_fields = {k: v for k, v in entity_fields.items() if v is not None}
    for field, value in entity_fields.items():
        v = ChangeValueStr(old_value=getattr(entity, field), new_value=value)
        db.add(v)
        db.flush()
        change = Change(
            change_request=change_request, 
            object_id=entity.id,
            field_name=field, 
            value_id=v.id,
            data_type=ChangeAttrType.STR, 
            content_type=ContentType.ENTITY, 
            change_type=ChangeType.UPDATE
        )
        db.add(change)

    schema = db.query(Schema).get(schema_id)
    _create_value_changes(db=db, change_request=change_request, schema=schema, data=data, new=False,
                          entity=entity)
    if commit:
        db.commit()
    else:
        db.flush()
    return change_request


def apply_entity_update_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: Optional[str] = None) -> Tuple[bool, Entity]:
    changes_query = (select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.change_type == ChangeType.UPDATE))
    entity_fields_changes = db.execute(
        changes_query.where(Change.field_name != None)
    ).scalars().all()
    other_fields_changes = db.execute(
        changes_query.where(Change.attribute_id != None)
    ).scalars().all()

    if not entity_fields_changes and not other_fields_changes \
            or change_request.object_type != EditableObjectType.ENTITY:
        raise MissingEntityUpdateRequestException(obj_id=change_request.id)

    entity = crud.get_entity_by_id(db=db, entity_id=change_request.object_id)
    attr_defs = {attr_def.attribute_id: attr_def for attr_def in entity.schema.attr_defs}

    single_changes = []
    listed_changes = defaultdict(list)
    for change in other_fields_changes:
        attr_def = attr_defs.get(change.attribute_id, None)
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=change.attribute_id, schema_id=entity.schema_id)

        if attr_def.list:
            listed_changes[change.attribute.name].append(change)
        else:
            single_changes.append(change)

    data = {}
    for change in entity_fields_changes:
        ValueModel = change.data_type.value.model
        value = db.execute(select(ValueModel).where(ValueModel.id == change.value_id)).scalar()
        data[change.field_name] = value.new_value

    for change in single_changes:
        ValueModel = change.data_type.value.model
        v = db.execute(select(ValueModel).where(ValueModel.id == change.value_id)).scalar()
        data[change.attribute.name] = v.new_value

    for attr_name, changes in listed_changes.items():
        ValueModel = changes[0].data_type.value.model
        value_ids = [i.value_id for i in changes]
        values = db.execute(select(ValueModel).where(ValueModel.id.in_(value_ids))).scalars().all()
        data[attr_name] = [i.new_value for i in values if i.new_value is not None]

    factory = EntityModelFactory()
    UpdateModel = factory(schema=entity.schema, variant=ModelVariant.UPDATE)
    entity = crud.update_entity(
        db=db, 
        id_or_slug=entity.id, 
        schema_id=entity.schema_id, 
        data=UpdateModel(**data).dict(exclude_unset=True),
        commit=False
    )
    change_request.status = ChangeStatus.APPROVED
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.reviewed_by_user_id = reviewed_by.id
    change_request.comment = comment
    db.commit()
    return True, entity


def create_entity_delete_request(db: Session, id_or_slug: Union[int, str], schema_id: int,
                                 created_by: User, commit: bool = True) -> ChangeRequest:
    crud.delete_entity(db=db, id_or_slug=id_or_slug, schema_id=schema_id, commit=False)
    db.rollback()
    schema = crud.get_schema(db=db, id_or_slug=schema_id)
    entity = crud.get_entity_model(db=db, id_or_slug=id_or_slug, schema=schema)

    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.ENTITY,
        object_id=entity.id,
        change_type=ChangeType.DELETE
    )
    db.add(change_request)

    val = ChangeValueBool(old_value=entity.deleted, new_value=True)
    db.add(val)
    db.flush()
    change = Change(
        change_request=change_request,
        data_type=ChangeAttrType.BOOL,
        change_type=ChangeType.DELETE,
        content_type=ContentType.ENTITY,
        object_id=entity.id,
        field_name='deleted',
        value_id=val.id
    )
    db.add(change)
    if commit:
        db.commit()
    else:
        db.flush()
    return change_request


def apply_entity_delete_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: Optional[str]) -> Tuple[bool, Entity]:
    change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.data_type == ChangeAttrType.BOOL)
        .where(Change.change_type == ChangeType.DELETE)
        .where(Change.content_type == ContentType.ENTITY)
        .where(Change.field_name == 'deleted')
        .where(Change.object_id != None)
    ).scalar()
    
    if change is None:
        raise MissingEntityDeleteRequestException(obj_id=change_request.id)
    entity = crud.get_entity_by_id(db=db, entity_id=change.object_id)
    v = db.execute(select(ChangeValueBool).where(ChangeValueBool.id == change.value_id)).scalar()
    v.old_value = entity.deleted
    entity = crud.delete_entity(
        db=db,
        id_or_slug=entity.id,
        schema_id=entity.schema_id,
        commit=False
    ) 
    change_request.status = ChangeStatus.APPROVED
    change_request.reviewed_by = reviewed_by
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.comment = comment
    db.commit()
    return True, entity
