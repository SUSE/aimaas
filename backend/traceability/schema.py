from datetime import datetime
from typing import Dict

from ..models import *
from ..schemas import *
from ..exceptions import *
from ..crud import *
from .. import crud


def get_recent_schema_changes(db: Session, schema_id: int, count: int = 5) -> SchemaChangeDetailSchema:
    # captures only updates and deletions of schemas
    return db.execute(
        select(Change)
        .where(Change.change_object == ChangeObject.SCHEMA)
        .join(SchemaUpdate)
        .where(SchemaUpdate.change_id == Change.id)
        .where(SchemaUpdate.schema_id == schema_id)
        .order_by(Change.created_at.desc()).limit(count)
    ).scalars().all()

def schema_change_details(db: Session, change_id: int):
    # TODO details for schema create?
    change = db.execute(select(Change).where(Change.id == change_id).where(Change.change_object == ChangeObject.SCHEMA)).scalar()
    if change is None:
        raise MissingChangeException(obj_id=change_id)
    upd = db.execute(select(SchemaUpdate).where(SchemaUpdate.change_id == change_id)).scalar()
    change_ = {'changes': {'add': [], 'update': [], 'delete': []}}
    change_['reviewed_at'] = change.reviewed_at
    change_['created_at'] = change.created_at
    change_['status'] = change.status
    change_['comment'] = change.comment
    change_['created_by'] = change.created_by.username
    change_['reviewed_by'] = change.reviewed_by.username if change.reviewed_by else None
    change_['schema'] = {'slug': upd.schema.slug, 'name': upd.schema.name, 'id': upd.schema.id}
    
    if upd.new_deleted is not None:
        change_['changes']['deleted'] = {'new': upd.new_deleted, 'old': upd.old_deleted, 'current': upd.schema.deleted}
        return SchemaChangeDetailSchema(**change_)

    if upd.new_name is not None:
        change_['changes']['name'] = {'new': upd.new_name, 'old': upd.old_name, 'current': upd.schema.name}
    if upd.new_slug is not None:
        change_['changes']['slug'] = {'new': upd.new_slug, 'old': upd.old_slug, 'current': upd.schema.slug}
    if upd.new_reviewable is not None:
        change_['changes']['reviewable'] = {'new': upd.new_reviewable, 'old': upd.old_reviewable, 'current': upd.schema.reviewable}

    attr_create = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    for attr in attr_create:
        d = attr.__dict__
        d['type'] = d['type'].name
        change_['changes']['add'].append(AttrDefSchema(**d))
    
    attr_upd = db.execute(select(AttributeUpdate).where(AttributeUpdate.change_id == change.id)).scalars().all()
    for attr in attr_upd:
        change_['changes']['update'].append(AttrDefUpdateSchema(**{**attr.__dict__, 'name': attr.attribute.name}))

    attr_del = db.execute(select(AttributeDelete).where(AttributeDelete.change_id == change.id)).scalars().all()
    change_['changes']['delete'] = [i.attribute.name for i in attr_del]

    return SchemaChangeDetailSchema(**change_)


def create_schema_create_request(db: Session, data: SchemaCreateSchema, created_by: User, commit: bool = True) -> Change:
    crud.create_schema(db=db, data=data, commit=False)
    db.rollback()

    change = Change(
        created_by=created_by, 
        created_at=datetime.utcnow(), 
        change_object=ChangeObject.SCHEMA, 
        change_type=ChangeType.CREATE
    )
    schema_create = SchemaCreate(change=change, name=data.name, slug=data.slug, reviewable=data.reviewable)
    db.add_all([change, schema_create])

    for attr in data.attributes:
        kwargs = attr.dict()
        kwargs['type'] = AttrType[kwargs['type'].name]
        db.add(AttributeCreate(change=change, **kwargs))
    if commit:
        db.commit()
    else:
        db.flush()
    return change


def apply_schema_create_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str] = None, commit: bool = True):
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.SCHEMA)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalar()
    if change is None:
        raise MissingSchemaCreateRequestException(obj_id=change_id)

    schema_create: SchemaCreate = db.execute(select(SchemaCreate).where(SchemaCreate.change_id == change.id)).scalar()
    attrs = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    data = SchemaCreateSchema(
        name=schema_create.name,
        slug=schema_create.slug,
        reviewable=schema_create.reviewable,
        attributes=[
            AttrDefSchema(
                name=i.name,
                type=i.type.name,
                required=i.required,
                unique=i.unique,
                list=i.list,
                key=i.key,
                description=i.description,
                bind_to_schema=i.bind_to_schema
            ) for i in attrs
        ]
    )

    change.reviewed_at = datetime.utcnow()
    change.reviewed_by_user_id = reviewed_by.id
    change.status = ChangeStatus.APPROVED
    change.comment = comment
    schema = create_schema(db=db, data=data, commit=False)
    if commit:
        db.commit()
    else:
        db.flush()
    return schema


def create_schema_update_request(db: Session, id_or_slug: Union[int, str], data: SchemaUpdateSchema, created_by: User, commit: bool = True):
    crud.update_schema(db=db, id_or_slug=id_or_slug, data=data, commit=False)
    db.rollback()
    schema = crud.get_schema(db=db, id_or_slug=id_or_slug)
    change = Change(created_by=created_by, created_at=datetime.utcnow(), change_object=ChangeObject.SCHEMA, change_type=ChangeType.UPDATE)
    schema_update = SchemaUpdate(
        change=change, 
        schema=schema, 
        new_name=data.name,
        new_reviewable=data.reviewable,
        new_slug=data.slug,
        old_name=schema.name,
        old_slug=schema.slug,
        old_reviewable=schema.reviewable
    )
    db.add_all([change, schema_update])
    attr_def_names: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in schema.attr_defs}
    for attr in data.update_attributes:
        attr_def = attr_def_names.get(attr.name)
        if attr.list:
            attr.unique = False

        attr_upd = AttributeUpdate(change=change, attribute=attr_def.attribute)
        attr_upd.required = attr.required if attr.required != attr_def.required else attr_def.required
        attr_upd.list = attr.list if attr.list != attr_def.list else attr_def.list
        attr_upd.key = attr.key if attr.key != attr_def.key else attr_def.key
        attr_upd.unique = attr.unique if attr.unique != attr_def.unique else attr_def.unique
        attr_upd.description = attr.description if attr.description != attr_def.description else attr_def.description
        attr_upd.new_name = attr.new_name
        db.add(attr_upd)

    for attr in data.add_attributes:
        attr_create = AttributeCreate(change=change)
        attr_create.name = attr.name
        attr_create.type = AttrType[attr.type.value]
        attr_create.required = attr.required
        attr_create.unique = attr.unique
        attr_create.list = attr.list
        attr_create.key = attr.key
        attr_create.description = attr.description

        if attr_create.type == AttrType.FK:
            if attr.bind_to_schema == -1:
                attr.bind_to_schema = schema.id
            attr_create.bind_to_schema = attr.bind_to_schema
        db.add(attr_create)

    for attr in data.delete_attributes:
        db.add(AttributeDelete(change=change, attribute=attr_def_names[attr].attribute))

    if commit: 
        db.commit()
    else:
        db.flush()
    return change


def apply_schema_update_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str] = None):
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.SCHEMA)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalar()
    if change is None:
        raise MissingSchemaUpdateRequestException(obj_id=change_id)
    schema_update: SchemaUpdate = db.execute(select(SchemaUpdate).where(SchemaUpdate.change_id == change.id)).scalar()
    attrs_update: List[AttributeUpdate] = db.execute(select(AttributeUpdate).where(AttributeUpdate.change_id == change.id)).scalars().all()
    attrs_create: List[AttributeCreate] = db.execute(select(AttributeCreate).where(AttributeCreate.change_id == change.id)).scalars().all()
    data = SchemaUpdateSchema(
        name=schema_update.new_name,
        slug=schema_update.new_slug,
        reviewable=schema_update.new_reviewable,
        update_attributes=[
            AttrDefUpdateSchema(
                name=i.attribute.name,
                new_name=i.new_name,
                required=i.required,
                unique=i.unique,
                list=i.list,
                key=i.key,
                description=i.description,
                bind_to_schema=i.bind_to_schema
            )
            for i in attrs_update
        ],
        add_attributes=[
            AttrDefSchema(
                name=i.name,
                type=i.type.name,
                required=i.required,
                unique=i.unique,
                list=i.list,
                key=i.key,
                description=i.description,
                bind_to_schema=i.bind_to_schema
            )
            for i in attrs_create
        ]
    )
    change.reviewed_at = datetime.utcnow()
    change.reviewed_by = reviewed_by
    change.status = ChangeStatus.APPROVED
    change.comment = comment
    s = update_schema(db=db, id_or_slug=schema_update.schema_id, data=data, commit=False)
    db.commit()
    return s


def create_schema_delete_request(db: Session, id_or_slug: Union[int, str], created_by: User, commit: bool = True) -> Change:
    crud.delete_schema(db=db, id_or_slug=id_or_slug, commit=False)
    db.rollback()
    if isinstance(id_or_slug, int):
        q = select(Schema).where(Schema.id == id_or_slug)
    else:
        q = select(Schema).where(Schema.slug == id_or_slug)
    schema = db.execute(q).scalar()
    
    change = Change(created_by=created_by, created_at=datetime.utcnow(), change_object=ChangeObject.SCHEMA, change_type=ChangeType.DELETE)
    sch_upd = SchemaUpdate(change=change, schema=schema, new_deleted=True, old_deleted=schema.deleted)
    db.add_all([change, sch_upd])
    if commit:
        db.commit()
    else:
        db.flush()
    return change


def apply_schema_delete_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str]) -> Schema:
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.SCHEMA)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalar()
    if change is None:
        raise MissingSchemaDeleteRequestException(obj_id=change_id)
    sch_upd: SchemaUpdate = db.execute(select(SchemaUpdate).where(SchemaUpdate.change_id == change.id)).scalar()
    schema = delete_schema(db=db, id_or_slug=sch_upd.schema_id, commit=False)
    change.status = ChangeStatus.APPROVED
    change.reviewed_by = reviewed_by
    change.reviewed_at = datetime.utcnow()
    change.comment = comment
    db.commit()
    return schema