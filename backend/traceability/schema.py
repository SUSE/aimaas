from datetime import datetime, timezone
from itertools import groupby
import typing

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.models import User
from ..models import Schema
from ..schemas.schema import AttrDefSchema, AttrDefUpdateSchema, SchemaCreateSchema, \
    AttributeCreateSchema, SchemaUpdateSchema, AttributeDefinition
from ..schemas.traceability import SchemaChangeDetailSchema
from .. import crud
from .. import exceptions

from .enum import EditableObjectType, ContentType, ChangeType, ChangeStatus
from .models import ChangeRequest, Change, ChangeValueInt, ChangeAttrType, ChangeValueBool, \
    ChangeValueStr


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
    # TODO details for schema create?
    change_request = db.execute(select(ChangeRequest).where(ChangeRequest.id == change_request_id)).scalar()
    if change_request is None:
        raise exceptions.MissingChangeException(obj_id=change_request_id)
    
    schema_query = (
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.SCHEMA)
    )

    schema_id = db.execute(schema_query.where(Change.field_name == 'id')).scalar()
    schema_changes = db.execute(schema_query.where(Change.field_name != 'id')).scalars().all()

    attr_change_query = (
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
    )
    attr_update = db.execute(
        attr_change_query
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalars().all()
    attr_create = db.execute(
        attr_change_query
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    attr_delete = db.execute(
        attr_change_query
        .where(Change.attribute_id != None)
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalars().all()
    
    if not schema_id or not any([schema_changes, attr_update, attr_create, attr_delete]):
        raise exceptions.MissingSchemaUpdateRequestException(obj_id=change_request_id)
    
    schema = crud.get_schema(db=db, id_or_slug=schema_id.object_id)
    # group changes by attribute id to get set of properties for each attribute
    attr_update = {k: [i for i in v] for k, v in groupby(attr_update, key=lambda x: x.object_id)}
    attr_create = {k: [i for i in v] for k, v in groupby(attr_create, key=lambda x: x.object_id)}

    change_ = {'changes': {'add': [], 'update': [], 'delete': []}}
    change_['object_type'] = change_request.object_type.name
    change_['change_type'] = change_request.change_type.name
    change_['reviewed_at'] = change_request.reviewed_at
    change_['created_at'] = change_request.created_at
    change_['status'] = change_request.status
    change_['comment'] = change_request.comment
    change_['created_by'] = change_request.created_by.username
    change_['reviewed_by'] = change_request.reviewed_by.username if change_request.reviewed_by else None
    change_['schema'] = {'slug': schema.slug, 'name': schema.name, 'id': schema.id,
                         'deleted': schema.deleted}

    deleted = [i for i in schema_changes if i.field_name == 'deleted']
    if deleted:
        deleted = deleted[0]
        v = db.execute(select(ChangeValueBool).where(ChangeValueBool.id == deleted.value_id)).scalar()
        change_['changes']['deleted'] = {'new': v.new_value, 'old': v.old_value,
                                         'current': schema.deleted}
        return exceptions.EntityChangeDetailSchema(**change_)

    for change in schema_changes:
        v = get_value_for_change(change, db)
        if v.new_value is None:
            continue
        change_['changes'][change.field_name] = {'old': v.old_value, 'new': v.new_value,
                                                 'current': getattr(schema, change.field_name)}

    for attr_id, changes in attr_create.items():
        change_['changes']['add'].append(AttrDefSchema(
            **{i.field_name: get_value_for_change(i, db).new_value for i in changes}
        ))

    for attr_id, changes in attr_update.items():
        attr = crud.get_attribute(db=db, attr_id=attr_id)
        change_['changes']['update'].append(AttrDefUpdateSchema(
           **{**{i.field_name: get_value_for_change(i, db).new_value for i in changes}, 'name': attr.name}
        ))

    for change in attr_delete:
        change_['changes']['delete'].append(change.attribute.name)

    return SchemaChangeDetailSchema(**change_)


def create_schema_create_request(db: Session, data: SchemaCreateSchema, created_by: User,
                                 commit: bool = True) -> ChangeRequest:
    crud.create_schema(db=db, data=data, commit=False)
    db.rollback()

    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.utcnow(),
        object_type=EditableObjectType.SCHEMA,
        change_type=ChangeType.CREATE
    )
    db.add(change_request)

    schema_fields = [('name', ChangeAttrType.STR), ('slug', ChangeAttrType.STR),
                     ('reviewable', ChangeAttrType.BOOL)]
    for field, type_ in schema_fields:
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

    attr_fields = [
        ('required', ChangeAttrType.BOOL), 
        ('unique', ChangeAttrType.BOOL), 
        ('list', ChangeAttrType.BOOL), 
        ('key', ChangeAttrType.BOOL),
        ('description', ChangeAttrType.STR),
        ('bind_to_schema', ChangeAttrType.INT),
        ('name', ChangeAttrType.STR),
        # ('type', ChangeAttrType.STR)
    ]
    for attr in data.attributes:
        a_data = AttributeCreateSchema(name=attr.name, type=attr.type.name)
        attribute = crud.create_attribute(db=db, data=a_data, commit=False)
        for field, type_ in attr_fields:
            ValueModel = type_.value.model
            v = ValueModel(new_value=getattr(attr, field))
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=field,
                object_id=attribute.id,
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
            ))
        v = ChangeValueStr(new_value=attr.type.name)
        db.add(v)
        db.flush()
        db.add(Change(
                change_request=change_request,
                field_name='type',
                value_id=v.id,
                object_id=attribute.id,
                data_type=ChangeAttrType.STR,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
        ))
    if commit:
        db.commit()
    else:
        db.flush()
    return change_request

def get_value_for_change(change: Change, db: Session):
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
        .where(Change.object_id != None)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    attr_changes = groupby(attr_changes, key=lambda x: x.object_id)
    for attr_id, changes in attr_changes:
        crud.get_attribute(db=db, attr_id=attr_id)
        data['attributes'].append({i.field_name: get_value_for_change(change=i, db=db).new_value for i in changes})
    data = SchemaCreateSchema(**data)

    schema = crud.create_schema(db=db, data=data, commit=False)
    change_request.object_id = schema.id
    change_request.reviewed_at = datetime.utcnow()
    change_request.reviewed_by_user_id = reviewed_by.id
    change_request.status = ChangeStatus.APPROVED
    change_request.comment = comment

    for change in schema_changes:     # setting object_id is required
        change.object_id = schema.id  # to be able to show details
    for change in attr_changes:       # for this change request
        change.object_id = schema.id

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
        created_at=datetime.utcnow(),
        object_type=EditableObjectType.SCHEMA,
        object_id=schema.id,
        change_type=ChangeType.UPDATE
    )
    db.add(change_request)
    
    schema_fields = [('name', ChangeAttrType.STR), ('slug', ChangeAttrType.STR),
                     ('reviewable', ChangeAttrType.BOOL)]
    for field, type_ in schema_fields:
        ValueModel = type_.value.model
        v = ValueModel(new_value=getattr(data, field))  # TODO old value
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
        change_type=ChangeType.UPDATE
    ))

    attr_fields = [
        ('required', ChangeAttrType.BOOL), 
        ('unique', ChangeAttrType.BOOL), 
        ('list', ChangeAttrType.BOOL), 
        ('key', ChangeAttrType.BOOL),
        ('description', ChangeAttrType.STR),
        ('bind_to_schema', ChangeAttrType.INT),
        ('name', ChangeAttrType.STR),
        ('new_name', ChangeAttrType.STR),
        # ('type', ChangeAttrType.STR)
    ]
    attr_def_names: typing.Dict[str, AttributeDefinition] = {i.attribute.name: i for i in schema.attr_defs}
    for attr in data.update_attributes:
        attribute = attr_def_names[attr.name].attribute
        for field, type_ in attr_fields:
            ValueModel = type_.value.model
            v = ValueModel(new_value=getattr(attr, field))
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=field,
                object_id=attribute.id,
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.UPDATE
            ))
    
    attr_fields = [
        ('required', ChangeAttrType.BOOL), 
        ('unique', ChangeAttrType.BOOL), 
        ('list', ChangeAttrType.BOOL), 
        ('key', ChangeAttrType.BOOL),
        ('description', ChangeAttrType.STR),
        ('bind_to_schema', ChangeAttrType.INT),
        ('name', ChangeAttrType.STR),
        # ('type', ChangeAttrType.STR)
    ]
    for attr in data.add_attributes:
        a_data = AttributeCreateSchema(name=attr.name, type=attr.type.name)
        attribute = crud.create_attribute(db=db, data=a_data, commit=False)
        for field, type_ in attr_fields:
            ValueModel = type_.value.model
            v = ValueModel(new_value=getattr(attr, field))
            db.add(v)
            db.flush()
            db.add(Change(
                change_request=change_request,
                field_name=field,
                object_id=attribute.id,
                value_id=v.id,
                data_type=type_,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
            ))
        v = ChangeValueStr(new_value=attr.type.name)
        db.add(v)
        db.flush()
        db.add(Change(
                change_request=change_request,
                field_name='type',
                value_id=v.id,
                object_id=attribute.id,
                data_type=ChangeAttrType.STR,
                content_type=ContentType.ATTRIBUTE_DEFINITION,
                change_type=ChangeType.CREATE
        ))
    for attr_name in data.delete_attributes:
        attribute = attr_def_names[attr_name].attribute
        v = ChangeValueStr(new_value=attr_name)  # this is not really needed in this case
        db.add(v)                                # but models require value_id
        db.flush()
        db.add(Change(
            change_request=change_request,
            attribute_id=attribute.id,
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

    schema_id = db.execute(schema_query.where(Change.field_name == 'id')).scalar()
    schema_changes = db.execute(schema_query.where(Change.field_name != 'id')).scalars().all()

    attr_change_query = (
        select(Change)
        .where(Change.change_request_id == change_request.id)
        .where(Change.content_type == ContentType.ATTRIBUTE_DEFINITION)
    )
    attr_upd = db.execute(
        attr_change_query
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalars().all()
    attr_create = db.execute(
        attr_change_query
        .where(Change.field_name != None)
        .where(Change.object_id != None)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalars().all()
    attr_delete = db.execute(
        attr_change_query
        .where(Change.attribute_id != None)
        .where(Change.data_type == ChangeAttrType.STR)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalars().all()
    
    if not schema_id or not any([schema_changes, attr_upd, attr_create, attr_delete]):
        raise exceptions.MissingSchemaUpdateRequestException(obj_id=change_request.id)
    schema_id = schema_id.object_id

    # group changes by attribute id to get set of properties for each attribute
    attr_upd = {k: [i for i in v] for k, v in groupby(attr_upd, key=lambda x: x.object_id)}
    attr_create = {k: [i for i in v] for k, v in groupby(attr_create, key=lambda x: x.object_id)}

    data = {'update_attributes': [], 'add_attributes': [], 'delete_attributes': []}
    for change in schema_changes:
        data[change.field_name] = get_value_for_change(change=change, db=db).new_value
    
    for attr_id, changes in attr_upd.items():
        data['update_attributes'].append(
            {i.field_name: get_value_for_change(i, db).new_value  for i in changes}
        )

    for attr_id, changes in attr_create.items():
        data['add_attributes'].append(
            {i.field_name: get_value_for_change(i, db).new_value  for i in changes}
        )

    for change in attr_delete:
        data['delete_attributes'].append(change.attribute.name)

    change_request.reviewed_at = datetime.utcnow()
    change_request.reviewed_by = reviewed_by
    change_request.status = ChangeStatus.APPROVED
    change_request.comment = comment
    schema = crud.update_schema(db=db, id_or_slug=schema_id, data=SchemaUpdateSchema(**data),
                                commit=False)
    db.commit()
    return True, schema


def create_schema_delete_request(db: Session, id_or_slug: typing.Union[int, str], created_by: User,
                                 commit: bool = True) -> ChangeRequest:
    crud.delete_schema(db=db, id_or_slug=id_or_slug, commit=False)
    db.rollback()
    schema = crud.get_schema(db=db, id_or_slug=id_or_slug)
    change_request = ChangeRequest(
        created_by=created_by, 
        created_at=datetime.utcnow(),
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
