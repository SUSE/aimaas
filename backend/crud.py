from typing import Dict, List, Union

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from .models import (
    AttrType,
    Attribute,
    AttributeDefinition,
    BoundFK,
    Entity,
    Schema,
)

from .schemas import (
    AttrDefSchema,
    AttrDefWithAttrDataSchema,
    AttributeDefinitionUpdateSchema,
    SchemaCreateSchema,
    SchemaUpdateSchema,
    AttributeCreateSchema
)
from .exceptions import *


RESERVED_ATTR_NAMES = ['id', 'slug', 'deleted']


def get_attributes(db: Session) -> List[Attribute]:
    return db.execute(select(Attribute)).scalars().all()


def get_attribute(db: Session, attr_id: int) -> Attribute:
    attr = db.execute(select(Attribute).where(Attribute.id == attr_id)).scalar()
    if attr is None:
        raise MissingAttributeException(obj_id=attr_id)
    return attr


def create_attribute(db: Session, data: AttributeCreateSchema, commit: bool = True) -> Attribute:
    if data.name in RESERVED_ATTR_NAMES:
        raise ReservedAttributeException(attr_name=data.name, reserved=RESERVED_ATTR_NAMES)

    attr = db.execute(
        select(Attribute)
        .where(Attribute.name == data.name)
        .where(Attribute.type == AttrType[data.type.value])
    ).scalar()
    if attr:
        return attr

    a = Attribute(name=data.name, type=AttrType[data.type.value])
    db.add(a)
    if commit:
        db.commit()  # This may raise IntegrityError if other session commits same data
    return a


def get_schemas(db: Session, all: bool = False, deleted_only: bool = False) -> List[Schema]:
    q = select(Schema)
    if all:
        pass
    elif deleted_only:
        q = q.where(Schema.deleted == True)
    else:
        q = q.where(Schema.deleted == False)
    return db.execute(q).scalars().all()


def get_schema(db: Session, id_or_slug: Union[int, str]) -> Schema:
    q = select(Schema)
    if isinstance(id_or_slug, int):
        q = q.where(Schema.id == id_or_slug)
    else:
        q = q.where(Schema.slug == id_or_slug)
        
    schema = db.execute(q).scalar()
    if schema is None:
        raise MissingSchemaException(obj_id=id_or_slug)
    return schema


def create_schema(db: Session, data: SchemaCreateSchema) -> Schema:
    try:
        sch = Schema(name=data.name, slug=data.slug)
        db.add(sch)
        db.flush()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)
    
    attr_names = set()
    for attr in data.attributes:
        if isinstance(attr, AttrDefSchema):
            a: Attribute = db.execute(select(Attribute).where(Attribute.id == attr.attr_id)).scalar()
            if a is None:
                raise MissingAttributeException(attr.attr_id)
        elif isinstance(attr, AttrDefWithAttrDataSchema):
            a = create_attribute(db, attr, commit=False)
            db.flush()
        
        if a.name in attr_names:
            raise MultipleAttributeOccurencesException(a.name)
        attr_names.add(a.name)

        ad = AttributeDefinition(
            attribute_id=a.id, 
            schema_id=sch.id,
            required=attr.required, 
            list=attr.list, 
            unique=attr.unique,
            key=attr.key,
            description=attr.description
        )
        db.add(ad)
        db.flush()
        if a.type == AttrType.FK:
            if attr.bind_to_schema is None:
                raise NoSchemaToBindException(attr_id=a.id)
            if attr.bind_to_schema == -1:
                s = sch
            else:
                s = db.execute(
                    select(Schema)
                    .where(Schema.id == attr.bind_to_schema)
                    .where(Schema.deleted == False)
                ).scalar()
            if s is None:
                raise MissingSchemaException(obj_id=attr.bind_to_schema)
            bfk = BoundFK(attr_def_id=ad.id, schema_id=s.id)
            db.add(bfk)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)
    return sch


def delete_schema(db: Session, schema_id: int) -> Schema:
    schema = db.execute(
        select(Schema)
        .where(Schema.id == schema_id)
        .where(Schema.deleted == False)
    ).scalar()
    if schema is None:
        raise MissingSchemaException(obj_id=schema_id)
    
    db.execute(
        update(Entity).where(Entity.schema_id == schema_id).values(deleted=True)
    )
    schema.deleted = True
    db.commit()
    return schema


def update_schema(db: Session, schema_id: int, data: SchemaUpdateSchema) -> Schema:
    sch: Schema = db.execute(
        select(Schema).where(Schema.id == schema_id).where(Schema.deleted == False)
    ).scalar()
    if sch is None:
        raise MissingSchemaException(obj_id=schema_id)
    
    try:
        db.execute(
            update(Schema)
            .where(Schema.id == schema_id)
            .values(name=data.name, slug=data.slug)
        )
    except:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)

    attr_def_ids: Dict[int, AttributeDefinition] = {i.id: i for i in sch.attr_defs}
    attr_def_names: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in sch.attr_defs}
    for attr in data.update_attributes:
        if isinstance(attr, AttributeDefinitionUpdateSchema):
            attr_def = attr_def_ids.get(attr.attr_def_id)
        else:
            attr_def = attr_def_names.get(attr.name)
        
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=attr.attr_def_id, schema_id=sch.id)
        if attr_def.list and not attr.list:
            raise ListedToUnlistedException(attr_def_id=attr_def.id)
        if attr.list:
            attr.unique = False
        attr_def.required = attr.required
        attr_def.unique = attr.unique
        attr_def.list = attr.list
        attr_def.key = attr.key
        attr_def.description = attr.description
    db.flush()
    
    attr_names = set()
    for attr in data.add_attributes:
        if isinstance(attr, AttrDefSchema):
            a: Attribute = db.execute(select(Attribute).where(Attribute.id == attr.attr_id)).scalar()
            if a is None:
                raise MissingAttributeException(obj_id=attr.attr_id)
        elif isinstance(attr, AttrDefWithAttrDataSchema):
            a = create_attribute(db, attr, commit=False)
            db.flush()
        
        if a.name in attr_names:
            raise MultipleAttributeOccurencesException(attr_name=a.name)
        attr_names.add(a.name)
        
        try:
            ad = AttributeDefinition(
                attribute_id=a.id, 
                schema_id=sch.id,
                required=attr.required, 
                list=attr.list, 
                unique=attr.unique if not attr.list else False,
                key=attr.key,
                description=attr.description
            )
            db.add(ad)
            db.flush()
        except sqlalchemy.exc.IntegrityError:
            db.rollback()
            raise AttributeAlreadyDefinedException(attr_id=a.id, schema_id=sch.id)
        
        if a.type == AttrType.FK:
            if attr.bind_to_schema is None:
                raise NoSchemaToBindException(attr_id=a.id)
            if attr.bind_to_schema == -1:
                s = sch
            else:
                s = db.execute(
                    select(Schema)
                    .where(Schema.id == attr.bind_to_schema)
                    .where(Schema.deleted == False)
                ).scalar()
            if s is None:
                raise MissingSchemaException(obj_id=attr.bind_to_schema)
            bfk = BoundFK(attr_def_id=ad.id, schema_id=s.id)
            db.add(bfk)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)
    return sch


def _get_entity_data(db: Session, entity: Entity, attr_names: List[str]) -> Dict[str, Any]:
    data = {'id': entity.id, 'slug': entity.slug, 'deleted': entity.deleted}
    for attr in attr_names:
        val_obj = entity.get(attr, db)
        try:
            data[attr] = val_obj.value if not isinstance(val_obj, list) else [i.value for i in val_obj]   
        except AttributeError:
            data[attr] = None
    return data


def get_entities(
        db: Session, 
        schema: Schema,
        limit: int = None,
        offset: int = None,
        all: bool = False, 
        deleted_only: bool = False, 
        all_fields: bool = False
    ) -> List[dict]:
    
    q = select(Entity).where(Entity.schema_id == schema.id)
    if not all:
        q = q.where(Entity.deleted == deleted_only)
    entities = db.execute(q.offset(offset).limit(limit)).scalars().all()

    attr_defs = schema.attr_defs if all_fields else [i for i in schema.attr_defs if i.key]
    data = []
    for e in entities:
        data.append(_get_entity_data(db, entity=e, attr_names=[i.attribute.name for i in attr_defs]))
    return data


def get_entity(db: Session, entity_id: int, schema: Schema) -> dict:
    e = db.execute(select(Entity).where(Entity.id == entity_id)).scalar()
    if e is None:
        raise MissingEntityException(obj_id=entity_id)
    if e.schema_id != schema.id:
        raise MismatchingSchemaException(entity_id=entity_id, schema_id=schema.id)

    attrs = [i.attribute.name for i in schema.attr_defs]
    return _get_entity_data(db=db, entity=e, attr_names=attrs)

        
def create_entity(db: Session, schema_id: int, data: dict) -> Entity:
    sch: Schema = db.execute(
        select(Schema).where(Schema.id == schema_id).where(Schema.deleted == False)
    ).scalar()
    if sch is None:
        raise MissingSchemaException(obj_id=schema_id)
    try:
        slug = data.pop('slug')
    except KeyError:
        raise RequiredFieldException(field='slug')

    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in sch.attr_defs}
    required = [i for i in attr_defs if attr_defs[i].required]
    for i in required:
        if i not in data:
            raise RequiredFieldException(field=i)

    e = Entity(schema_id=schema_id, slug=slug)
    db.add(e)
    try:
        db.flush()
    except sqlalchemy.exc.IntegrityError:
        raise EntityExistsException(slug=slug)

    for field, value in data.items():
        attr_def = attr_defs.get(field)
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=None, schema_id=schema_id)
        
        attr: Attribute = attr_def.attribute
        model, caster = attr.type.value
        try:
            if isinstance(value, list):
                if not attr_def.list:
                    raise NotListedAttributeException(attr_name=attr.name, schema_id=sch.id)
                values = [caster(i) for i in value]
            else:
                values = [caster(value)]
        except ValueError as e:
            raise # can this even happen with validation done before?
        
        if attr.type == AttrType.FK:
            bound_schema_id = db.execute(
                select(BoundFK.schema_id)
                .where(BoundFK.attr_def_id == attr_def.id)
            ).scalar()
            for id_ in values:
                entity = db.execute(
                    select(Entity)
                    .where(Entity.id == id_)
                    .where(Entity.deleted == False)
                ).scalar()
                if entity is None:
                    raise MissingEntityException(obj_id=id_)
                if entity.schema_id != bound_schema_id:
                    raise WrongSchemaToBindException(
                        attr_name=attr.name, 
                        schema_id=sch.id, 
                        bound_schema_id=bound_schema_id, 
                        passed_entity=entity
                    )

        if attr_def.unique and not attr_def.list:
            existing = db.execute(
                select(model)
                .where(model.attribute_id == attr.id)
                .where(Entity.schema_id == schema_id)
                .where(model.value == values[0])
                .join(Entity, Entity.id == model.entity_id)
            ).scalars().all()
            if existing:
                for val in existing:
                    if not val.entity.deleted:
                        raise UniqueValueException(attr_name=attr.name, schema_id=sch.id, value=val.value)
        for val in values:
            v = model(value=val, entity_id=e.id, attribute_id=attr.id)
            db.add(v)
    db.commit()
    return e


def delete_entity(db: Session, entity_id: int) -> Entity:
    e = db.execute(
        select(Entity)
        .where(Entity.id == entity_id)
        .where(Entity.deleted == False)
    ).scalar()
    if e is None:
        raise MissingEntityException(obj_id=entity_id)
    e.deleted = True
    db.commit()
    return e