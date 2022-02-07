import enum
from datetime import datetime, timezone
from itertools import groupby, chain
import typing

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from ..auth.models import User
from ..models import Schema
from ..schemas.schema import AttrDefSchema, SchemaCreateSchema, SchemaUpdateSchema, \
    AttributeDefinition, SchemaBaseSchema
from ..schemas.traceability import SchemaChangeDetailSchema, ChangeSchema
from .. import crud
from .. import exceptions

from .enum import EditableObjectType, ContentType, ChangeType, ChangeStatus
from .models import ChangeRequest, Change, ChangeValueInt, ChangeAttrType, ChangeValueBool, \
    ChangeValueStr, ChangeValue


SCHEMA_FIELDS = [
    ('name', ChangeAttrType.STR),
    ('slug', ChangeAttrType.STR),
    ('reviewable', ChangeAttrType.BOOL)
]
ATTRIBUTE_FIELDS = [
    ('name', ChangeAttrType.STR),
    ('type', ChangeAttrType.STR),
]
DEFINITION_FIELDS = [
    ('required', ChangeAttrType.BOOL),
    ('unique', ChangeAttrType.BOOL),
    ('list', ChangeAttrType.BOOL),
    ('key', ChangeAttrType.BOOL),
    ('description', ChangeAttrType.STR),
    ('bound_schema_id', ChangeAttrType.INT),
]
FIELD_MAP = {
    'bound_schema_id': 'bound_schema_id'
}


def get_pending_entity_create_requests_for_schema(db: Session, schema_id: int) -> typing.List[ChangeRequest]:
    q = (
        select(ChangeRequest)
        .where(ChangeRequest.status == ChangeStatus.PENDING)
        .where(ChangeRequest.change_type == ChangeType.CREATE)
        .where(ChangeRequest.object_type == EditableObjectType.ENTITY)
        .join(Change)
        .where(Change.field_name == 'schema_id')
        .join(ChangeValueInt, Change.value_id == ChangeValueInt.id)
        .where(ChangeValueInt.new_value == schema_id)
    )
    return db.execute(q).scalars().all()


def get_recent_schema_changes(db: Session, schema_id: int, count: int = 5) \
        -> typing.Tuple[typing.List[ChangeRequest], typing.List[ChangeRequest]]:
    schema_changes = db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.object_id == schema_id)
        .where(ChangeRequest.object_type == EditableObjectType.SCHEMA)
        .order_by(ChangeRequest.created_at.desc()).limit(count)
        .distinct()
    ).scalars().all()
    pending_entity_requests = get_pending_entity_create_requests_for_schema(db=db, schema_id=schema_id)
    return schema_changes, pending_entity_requests


def schema_change_details(db: Session, change_request_id: int) -> SchemaChangeDetailSchema:
    try:
        change_request = db\
            .query(ChangeRequest)\
            .filter(ChangeRequest.id == change_request_id,
                    ChangeRequest.object_type == EditableObjectType.SCHEMA)\
            .one()
    except NoResultFound:
        raise exceptions.MissingChangeRequestException(obj_id=change_request_id)

    schema_changes = db\
        .query(Change)\
        .filter(Change.change_request_id == change_request.id,
                Change.field_name != None,
                Change.field_name != 'id',
                Change.content_type == ContentType.SCHEMA)

    attr_changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .order_by(Change.object_id)
    ).scalars().all()

    schema, attr_defs = None, None
    if change_request.object_id:
        schema = crud.get_schema(db=db, id_or_slug=change_request.object_id)
        attr_defs = {d.attribute.name: d for d in schema.attr_defs}

    change_ = {
        'changes': {},
        'object_type': change_request.object_type.name,
        'change_type': change_request.change_type.name,
        'reviewed_at': change_request.reviewed_at,
        'created_at': change_request.created_at,
        'status': change_request.status,
        'comment': change_request.comment,
        'created_by': change_request.created_by.username,
        'reviewed_by': change_request.reviewed_by.username if change_request.reviewed_by else None,
        'schema': SchemaBaseSchema.from_orm(schema) if schema else None
    }

    deleted = [i for i in schema_changes if i.field_name == 'deleted']
    if deleted:
        deleted = deleted[0]
        v = db.execute(select(ChangeValueBool).where(ChangeValueBool.id == deleted.value_id)).scalar()
        change_['changes']['deleted'] = {'new': v.new_value, 'old': v.old_value,
                                         'current': schema.deleted}
        return SchemaChangeDetailSchema(**change_)

    for change in schema_changes:
        v = get_value_for_change(change, db)
        if v.new_value is None:
            continue
        change_['changes'][change.field_name] = {'old': v.old_value, 'new': v.new_value,
                                                 'current': getattr(schema, change.field_name, None)}

    for change in attr_changes:
        v = get_value_for_change(change, db)
        if change.field_name:
            attr_name, field_name = change.field_name.split(".", maxsplit=1)
        else:
            attr_name, field_name = change.attribute.name, None

        if not attr_defs or attr_name not in attr_defs:
            current_value = None
        elif field_name in ["name", "type"]:
            current_value = getattr(attr_defs.get(attr_name).attribute, field_name)
        elif field_name is None:
            current_value = attr_name
        else:
            current_value = getattr(attr_defs.get(attr_name), field_name, None)
        if isinstance(current_value, enum.Enum):
            current_value = current_value.name
        change_["changes"][change.field_name or attr_name] = ChangeSchema(
            old=v.old_value,
            current=current_value,
            new=v.new_value
        )

    return SchemaChangeDetailSchema(**change_)


def create_schema_create_request(db: Session, data: SchemaCreateSchema, created_by: User,
                                 commit: bool = True) -> ChangeRequest:
    crud.create_schema(db=db, data=data, commit=False)
    db.rollback()

    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.SCHEMA,
        change_type=ChangeType.CREATE
    )
    db.add(change_request)

    for field, type_ in SCHEMA_FIELDS:
        ValueModel = type_.value.model
        v = ValueModel(new_value=getattr(data, field))
        db.add(v)
        db.flush()
        db.add(Change(
            change_request=change_request,
            field_name=field,
            value_id=v.id,
            data_type=type_,
            content_type=ContentType.SCHEMA,
            change_type=ChangeType.CREATE
        ))

    for attr in data.attributes:
        for field, type_ in chain(ATTRIBUTE_FIELDS, DEFINITION_FIELDS):
            ValueModel = type_.value.model
            new_value = getattr(attr, field)
            if isinstance(new_value, enum.Enum):
                new_value = new_value.value
            v = ValueModel(new_value=new_value)
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=f"{attr.name}.{field}",
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
            ))
    if commit:
        db.commit()
    else:
        db.flush()
    return change_request


def get_value_for_change(change: Change, db: Session) -> ChangeValue:
    ValueModel = change.data_type.value.model
    return db.execute(select(ValueModel).where(ValueModel.id == change.value_id)).scalar()


def apply_schema_create_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: typing.Optional[str] = None, commit: bool = True) \
        -> typing.Tuple[bool, Schema]:
    schema_changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id == None)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    if not schema_changes:
        raise exceptions.MissingSchemaCreateRequestException(obj_id=change_request.id)
    
    data = {'attributes': []}
    for change in schema_changes:
        v = get_value_for_change(change=change, db=db)
        data[change.field_name] = v.new_value
    
    attr_changes = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id == None)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    grouped_attr_changes = groupby(attr_changes, key=lambda x: x.field_name.split(".", maxsplit=1)[0])
    for attr_name, changes in grouped_attr_changes:
        attr_data = {"name": attr_name}
        for change in changes:
            attr_name2, field_name = change.field_name.split(".", maxsplit=1)
            assert attr_name2 == attr_name
            attr_data[field_name] = get_value_for_change(change=change, db=db).new_value
        data["attributes"].append(attr_data)
    data = SchemaCreateSchema(**data)

    schema = crud.create_schema(db=db, data=data, commit=False)
    change_request.object_id = schema.id
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.reviewed_by_user_id = reviewed_by.id
    change_request.status = ChangeStatus.APPROVED
    change_request.comment = comment

    attr_defs = {d.attribute.name: d.id for d in schema.attr_defs}
    for change in schema_changes:     # setting object_id is required
        change.object_id = schema.id  # to be able to show details
    for change in attr_changes:       # for this change request
        attr_name = change.field_name.split(".", maxsplit=1)[0]
        change.object_id = attr_defs.get(attr_name)

    v = ChangeValueInt(new_value=schema.id)
    db.add(v)
    db.flush()
    db.add(Change(
        change_request=change_request,
        field_name='id',
        value_id=v.id,
        object_id=schema.id,
        data_type=ChangeAttrType.INT,
        content_type=ContentType.SCHEMA,
        change_type=ChangeType.CREATE
    ))
    if commit:
        db.commit()
    else:
        db.flush()
    return True, schema


def create_schema_update_request(db: Session, id_or_slug: typing.Union[int, str],
                                 data: SchemaUpdateSchema, created_by: User, commit: bool = True) \
        -> ChangeRequest:
    crud.update_schema(db=db, id_or_slug=id_or_slug, data=data, commit=False)
    db.rollback()
    schema = crud.get_schema(db=db, id_or_slug=id_or_slug)

    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.SCHEMA,
        object_id=schema.id,
        change_type=ChangeType.UPDATE
    )
    db.add(change_request)

    for field, type_ in SCHEMA_FIELDS:
        new_value, old_value = getattr(data, field), getattr(schema, field)
        if new_value == old_value:
            continue
        ValueModel = type_.value.model
        v = ValueModel(new_value=new_value, old_value=old_value)
        db.add(v)
        db.flush()
        db.add(Change(
            change_request=change_request,
            field_name=field,
            value_id=v.id,
            object_id=schema.id,
            data_type=type_,
            content_type=ContentType.SCHEMA,
            change_type=ChangeType.UPDATE
        ))

    attr_map: typing.Dict[int, AttributeDefinition] = {i.id: i for i in schema.attr_defs}

    added, updated, deleted = crud.sort_attribute_definitions(schema=schema,
                                                              definitions=data.attributes)
    for attr in updated:
        attr_def = attr_map.get(attr.id)
        for field, type_ in ATTRIBUTE_FIELDS:
            cfield = FIELD_MAP.get(field, field)
            ValueModel = type_.value.model
            new_value = getattr(attr, field)
            old_value = getattr(attr_def.attribute, cfield)
            if isinstance(new_value, enum.Enum):
                new_value = new_value.name
            if isinstance(old_value, enum.Enum):
                old_value = old_value.name
            if old_value == new_value:
                continue
            v = ValueModel(new_value=new_value, old_value=old_value)
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=f"{attr.name}.{field}",
                object_id=attr_def.id,
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.UPDATE
            ))
        for field, type_ in DEFINITION_FIELDS:
            cfield = FIELD_MAP.get(field, field)
            ValueModel = type_.value.model
            new_value = getattr(attr, field)
            old_value = getattr(attr_def, cfield)
            if isinstance(new_value, enum.Enum):
                new_value = new_value.name
            if isinstance(old_value, enum.Enum):
                old_value = old_value.name
            if new_value == old_value:
                continue
            v = ValueModel(new_value=new_value, old_value=old_value)
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=f"{attr.name}.{field}",
                object_id=attr_def.id,
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.UPDATE
            ))

    for attr in added:
        for field, type_ in chain(ATTRIBUTE_FIELDS, DEFINITION_FIELDS):
            ValueModel = type_.value.model
            new_value = getattr(attr, field)
            if isinstance(new_value, enum.Enum):
                new_value = new_value.name
            v = ValueModel(new_value=new_value)
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=f"{attr.name}.{field}",
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
            ))

    for attr_def in deleted:
        v = ChangeValueStr(old_value=attr_def.attribute.name)
        db.add(v)
        db.flush()
        db.add(Change(
            change_request=change_request,
            object_id=attr_def.id,
            attribute_id=attr_def.attribute_id,
            value_id=v.id,
            data_type=ChangeAttrType.STR,
            content_type=ContentType.ATTRIBUTE_DEFINITION,
            change_type=ChangeType.DELETE
        ))

    if commit: 
        db.commit()
    else:
        db.flush()
    return change_request


def apply_schema_update_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: typing.Optional[str] = None) -> typing.Tuple[bool, Schema]:
    schema_query = (
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.UPDATE)
    )

    schema = change_request.schema
    attr_defs = {d.id: d for d in schema.attr_defs}
    schema_changes = db.execute(schema_query.where(Change.field_name != 'id')).scalars().all()

    attr_changes = db.query(Change)\
        .filter(Change.change_request_id == change_request.id,
                Change.content_type == ContentType.ATTRIBUTE_DEFINITION)\
        .all()

    if not schema or not any([schema_changes, attr_changes]):
        raise exceptions.MissingSchemaUpdateRequestException(obj_id=change_request.id)

    attributes = []
    for key, changes in groupby((a for a in attr_changes if a.change_type == ChangeType.UPDATE),
                                key=lambda x: x.object_id):
        attr_data = AttrDefSchema.from_orm(attr_defs.get(key))
        for change in changes:
            attr_name, field_name = change.field_name.split(".", maxsplit=1)
            if attr_name not in attr_data:
                setattr(attr_data, "name", attr_name)
            setattr(attr_data, field_name, get_value_for_change(change=change, db=db).new_value)
        attributes.append(attr_data)
    for key, changes in groupby((a for a in attr_changes if a.change_type == ChangeType.CREATE),
                                key=lambda x: x.field_name.split(".", maxsplit=1)[0]):
        attr_data = {"name": key}
        for change in changes:
            attr_name, field_name = change.field_name.split(".", maxsplit=1)
            assert key == attr_name
            attr_data[field_name] = get_value_for_change(change=change, db=db).new_value
        attributes.append(AttrDefSchema(**attr_data))

    unchanged_attributes = [AttrDefSchema.from_orm(a)
                            for a_id, a in attr_defs.items()
                            if a_id not in [_a.object_id for _a in attr_changes if _a.object_id]]

    data = {"attributes": attributes + unchanged_attributes}
    for change in schema_changes:
        data[change.field_name] = get_value_for_change(change=change, db=db).new_value
    
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.reviewed_by = reviewed_by
    change_request.status = ChangeStatus.APPROVED
    change_request.comment = comment
    schema = crud.update_schema(db=db, id_or_slug=schema.id, data=SchemaUpdateSchema(**data),
                                commit=False)
    db.refresh(schema)
    created_attr_defs = {d.attribute.name: d.id for d in schema.attr_defs}
    for change in attr_changes:
        if change.change_type == ChangeType.CREATE and not change.object_id:
            attr_name = change.field_name.split(".", maxsplit=1)[0]
            change.object_id = created_attr_defs.get(attr_name)
            if change.object_id is None:
                raise ValueError()
    db.commit()
    return True, schema


def create_schema_delete_request(db: Session, id_or_slug: typing.Union[int, str], created_by: User,
                                 commit: bool = True) -> ChangeRequest:
    crud.delete_schema(db=db, id_or_slug=id_or_slug, commit=False)
    db.rollback()
    schema = crud.get_schema(db=db, id_or_slug=id_or_slug)
    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.now(timezone.utc),
        object_type=EditableObjectType.SCHEMA,
        object_id=schema.id,
        change_type=ChangeType.DELETE
    )
    db.add(change_request)
    v = ChangeValueBool(old_value=schema.deleted, new_value=True)
    db.add(v)
    db.flush()
    db.add(
        Change(
            change_request=change_request,
            field_name='deleted',
            value_id=v.id,
            object_id=schema.id,
            data_type=ChangeAttrType.BOOL,
            content_type=ContentType.SCHEMA,
            change_type=ChangeType.DELETE
        )
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return change_request


def apply_schema_delete_request(db: Session, change_request: ChangeRequest, reviewed_by: User,
                                comment: typing.Optional[str]) -> typing.Tuple[bool, Schema]:
    change = db.execute(
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name == 'deleted')
        .where(Change.object_id != None)
        .where(Change.data_type == ChangeAttrType.BOOL)
        .where(Change.content_type == ContentType.SCHEMA)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalar()
    if change is None:
        raise exceptions.MissingSchemaDeleteRequestException(obj_id=change_request.id)

    v = get_value_for_change(change=change, db=db)
    if not v.new_value:
        raise exceptions.MissingSchemaDeleteRequestException(obj_id=change_request.id)

    schema = crud.delete_schema(db=db, id_or_slug=change.object_id, commit=False)
    change_request.status = ChangeStatus.APPROVED
    change_request.reviewed_by = reviewed_by
    change_request.reviewed_at = datetime.now(timezone.utc)
    change_request.comment = comment
    db.commit()
    return True, schema
