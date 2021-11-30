from copy import deepcopy
from datetime import datetime
from typing import Dict
from collections import defaultdict


from ..models import *
from ..schemas import *
from ..exceptions import *
from ..crud import *
from .. import crud
from .. import dynamic_routes


def get_recent_entity_changes(db: Session, entity_id: int, count: int = 5) -> List[Change]:
    # captures only updates and deletions of entities
    return db.execute(
        select(Change)
        .where(Change.change_object == ChangeObject.ENTITY)
        .join(EntityUpdate)
        .where(EntityUpdate.change_id == Change.id)
        .where(EntityUpdate.entity_id == entity_id)
        .order_by(Change.created_at.desc()).limit(count)
    ).scalars().all()


def entity_change_details(db: Session, change_id: int) -> EntityChangeDetailSchema:
    # TODO details for entity create?
    change = db.execute(select(Change).where(Change.id == change_id).where(Change.change_object == ChangeObject.ENTITY)).scalar()
    if change is None:
        raise MissingChangeException(obj_id=change_id)
    upd = db.execute(select(EntityUpdate).where(EntityUpdate.change_id == change_id)).scalar()
    change_ = {'changes': {}}
    change_['reviewed_at'] = change.reviewed_at
    change_['created_at'] = change.created_at
    change_['status'] = change.status
    change_['comment'] = change.comment
    change_['created_by'] = change.created_by.username
    change_['reviewed_by'] = change.reviewed_by.username if change.reviewed_by else None
    change_['entity'] = {'slug': upd.entity.slug, 'name': upd.entity.name, 'schema': upd.entity.schema.slug}

    if upd.new_deleted is not None:
        change_['changes']['deleted'] = {'new': upd.new_deleted, 'old': upd.old_deleted, 'current': upd.entity.deleted}
        return EntityChangeDetailSchema(**change_)

    if upd.new_name is not None:
        change_['changes']['name'] = {'new': upd.new_name, 'old': upd.old_name, 'current': upd.entity.name}
    if upd.new_slug is not None:
        change_['changes']['slug'] = {'new': upd.new_slug, 'old': upd.old_slug, 'current': upd.entity.slug}
    
    val_upds = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change.id)).scalars().all()
    attr_defs = db.execute(
        select(AttributeDefinition)
        .where(AttributeDefinition.schema_id == upd.entity.schema_id)
        .where(AttributeDefinition.attribute_id.in_([i.attribute_id for i in val_upds]))
    ).scalars().all()
    listed_ids = [i.attribute_id for i in attr_defs if i.list]
    listed = {i: [j for j in val_upds if j.attribute_id == i] for i in listed_ids}
    for upd in val_upds:
        attr = upd.attribute
        if upd.attribute.id in listed:
            change_['changes'][attr.name] = {'new': [i.new_value for i in listed[upd.attribute_id]], 'old': None, 'current': None}
        else:
            change_['changes'][attr.name] = {'new': upd.new_value, 'old': upd.old_value, 'current': get_old_value(db, upd.entity, attr.name)}
    return EntityChangeDetailSchema(**change_)
    

def get_old_value(db: Session, entity: Entity, attr_name: str) -> Any:
    val = entity.get(attr_name, db)
    if isinstance(val, list):
        return None
    return str(val.value) if val is not None else None


def create_entity_create_request(db: Session, data: dict, schema_id: int, created_by: User, commit: bool = True):
    crud.create_entity(db=db, schema_id=schema_id, data=deepcopy(data), commit=False)
    db.rollback()
    
    sch: Schema = db.execute(
        select(Schema).where(Schema.id == schema_id).where(Schema.deleted == False)
    ).scalar()

    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in sch.attr_defs}
    change = Change(created_by=created_by, created_at=datetime.utcnow(), change_object=ChangeObject.ENTITY, change_type=ChangeType.CREATE)
    ent_create = EntityCreate(change=change, name=data.pop('name'), slug=data.pop('slug'), schema_id=schema_id)
    db.add_all([change, ent_create])

    for field, value in data.items():
        attr_def = attr_defs.get(field)
        attr: Attribute = attr_def.attribute
        model, caster = attr.type.value
        values = crud._convert_values(attr_def=attr_def, value=value, caster=caster) or [None]
        for val in values:
            db.add(ValueUpdate(
                change=change,
                attribute=attr,
                new_value=str(val) if val is not None and not isinstance(val, bool) else val
            ))
    if commit:
        db.commit()
    else:
        db.flush()
    return change


def apply_entity_create_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str] = None):
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.ENTITY)
        .where(Change.change_type == ChangeType.CREATE)
    ).scalar()
    if change is None:
        raise MissingEntityCreateRequestException(obj_id=change_id)
    
    ent_create: EntityCreate = db.execute(select(EntityCreate).where(EntityCreate.change_id == change.id)).scalar()
    val_create: List[ValueUpdate] = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change.id)).scalars().all()

    single_values = []
    listed_values = defaultdict(list)
    for v in val_create:
        attr_def = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == ent_create.schema_id)
            .where(AttributeDefinition.attribute_id == v.attribute_id)
        ).scalar()
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=v.attribute_id, schema_id=ent_create.schema_id)
        if attr_def.list:
            listed_values[v.attribute.name].append(v)
        else:
            single_values.append(v)

    EntityCreateModel = dynamic_routes._create_entity_request_model(schema=ent_create.schema)
    data = {'name': ent_create.name, 'slug': ent_create.slug}
    for v in single_values:
        data[v.attribute.name] = v.new_value
    
    for attr_name, values in listed_values.items():
        data[attr_name] = [i.new_value for i in values if i.new_value is not None]

    e = create_entity(
        db=db, 
        schema_id=ent_create.schema_id, 
        data=EntityCreateModel(**data).dict(),
        commit=False
    )
    change.status = ChangeStatus.APPROVED
    change.reviewed_by = reviewed_by
    change.reviewed_at = datetime.utcnow()
    change.comment = comment
    for v in val_create:
        v.entity = e
    db.commit()
    return e


def create_entity_update_request(db: Session, id_or_slug: Union[int, str], schema_id: int, data: dict, created_by: User, commit: bool = True):
    crud.update_entity(db=db, id_or_slug=id_or_slug, schema_id=schema_id, data=deepcopy(data), commit=False)
    db.rollback()
    if isinstance(id_or_slug, int):
        q = select(Entity).where(Entity.id == id_or_slug)
    else:
        q = select(Entity).where(Entity.slug == id_or_slug)
    entity = db.execute(q).scalar()
    
    slug = data.pop('slug', None)
    name = data.pop('name', None)
    change = Change(created_by=created_by, created_at=datetime.utcnow(), change_object=ChangeObject.ENTITY, change_type=ChangeType.UPDATE)
    ent_upd = EntityUpdate(change=change, entity=entity, new_name=name, new_slug=slug, old_name=entity.name, old_slug=entity.slug)
    db.add_all([change, ent_upd])
    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in entity.schema.attr_defs}
    for field, value in data.items():
        attr_def = attr_defs.get(field)
        attr: Attribute = attr_def.attribute
        model, caster = attr.type.value
        if value is None:
            db.add(ValueUpdate(
                change=change,
                entity=entity,
                attribute=attr,
                new_value=None,
                old_value=get_old_value(db, entity, field)
            ))
            continue
        values = crud._convert_values(attr_def=attr_def, value=value, caster=caster)
        for val in values:
            db.add(ValueUpdate(
                change=change,
                entity=entity,
                attribute=attr,
                new_value=str(val) if val is not None and not isinstance(val, bool) else val,
                old_value=get_old_value(db, entity, field)
            ))
    if commit:
        db.commit()
    else:
        db.flush()
    return change


def apply_entity_update_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str] = None):
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.ENTITY)
        .where(Change.change_type == ChangeType.UPDATE)
    ).scalar()
    if change is None:
        raise MissingEntityUpdateRequestException(obj_id=change_id)
    ent_upd: EntityUpdate = db.execute(select(EntityUpdate).where(EntityUpdate.change_id == change.id)).scalar()
    val_upd: List[ValueUpdate] = db.execute(select(ValueUpdate).where(ValueUpdate.change_id == change.id)).scalars().all()

    single_values = []
    listed_values = defaultdict(list)
    for v in val_upd:
        attr_def = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == ent_upd.entity.schema_id)
            .where(AttributeDefinition.attribute_id == v.attribute_id)
        ).scalar()
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=v.attribute_id, schema_id=ent_upd.entity.schema_id)
        if attr_def.list:
            listed_values[v.attribute.name].append(v)
        else:
            single_values.append(v)
            v.old_value = str(get_old_value(db=db, entity=ent_upd.entity, attr_name=v.attribute.name))

    UpdateModel = dynamic_routes._update_entity_request_model(schema=ent_upd.entity.schema)
    data = {}
    if ent_upd.new_name is not None:
        data['name'] = ent_upd.new_name
    if ent_upd.new_slug is not None:
        data['slug'] = ent_upd.new_slug
    for v in single_values:
        data[v.attribute.name] = v.new_value
    
    for attr_name, values in listed_values.items():
        data[attr_name] = [i.new_value for i in values]

    result = update_entity(
        db=db, 
        id_or_slug=ent_upd.entity_id, 
        schema_id=ent_upd.entity.schema_id, 
        data=UpdateModel(**data).dict(exclude_unset=True),
        commit=False
    )
    change.status = ChangeStatus.APPROVED
    change.reviewed_at = datetime.utcnow()
    change.reviewed_by_user_id = reviewed_by.id
    change.comment = comment
    db.commit()
    return result


def create_entity_delete_request(db: Session, id_or_slug: Union[int, str], schema_id: int, created_by: User, commit: bool = True) -> Change:
    crud.delete_entity(db=db, id_or_slug=id_or_slug, schema_id=schema_id, commit=False)
    db.rollback()
    if isinstance(id_or_slug, int):
        q = select(Entity).where(Entity.id == id_or_slug)
    else:
        q = select(Entity).where(Entity.slug == id_or_slug)
    entity = db.execute(q).scalar()
    
    change = Change(created_by=created_by, created_at=datetime.utcnow(), change_object=ChangeObject.ENTITY, change_type=ChangeType.DELETE)
    ent_upd = EntityUpdate(change=change, entity=entity, new_deleted=True, old_deleted=entity.deleted)
    db.add_all([change, ent_upd])
    if commit:
        db.commit()
    else:
        db.flush()
    return change


def apply_entity_delete_request(db: Session, change_id: int, reviewed_by: User, comment: Optional[str]):
    change = db.execute(
        select(Change)
        .where(Change.id == change_id)
        .where(Change.change_object == ChangeObject.ENTITY)
        .where(Change.change_type == ChangeType.DELETE)
    ).scalar()
    if change is None:
        raise MissingEntityDeleteRequestException(obj_id=change_id)
    ent_upd: EntityUpdate = db.execute(select(EntityUpdate).where(EntityUpdate.change_id == change.id)).scalar()
    e = delete_entity(
        db=db, 
        id_or_slug=ent_upd.entity_id, 
        schema_id=ent_upd.entity.schema_id, 
        commit=False
    )
    change.status = ChangeStatus.APPROVED
    change.reviewed_by = reviewed_by
    change.reviewed_at = datetime.utcnow()
    change.comment = comment
    db.commit()
    return e