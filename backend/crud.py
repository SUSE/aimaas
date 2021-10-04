from typing import Dict
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
    SchemaCreateSchema,
    SchemaUpdateSchema,
    AttributeCreateSchema
)


def create_attribute(db: Session, data: AttributeCreateSchema, commit: bool = True) -> Attribute:
    attr = db.execute(
        select(Attribute)
        .where(Attribute.name == data.name)
        .where(Attribute.type == data.type)
    ).scalar()
    if attr:
        return attr

    a = Attribute(name=data.name, type=data.type)
    db.add(a)
    if commit:
        db.commit()
    return a


def create_schema(db: Session, data: SchemaCreateSchema) -> Schema:
    # TODO require lock here and in update?
    try:
        sch = Schema(name=data.name, slug=data.slug)
        db.add(sch)
        db.flush()
    except sqlalchemy.exc.IntegrityError:
        raise Exception(f'Schema with name `{data.name}` or slug `{data.slug}` already exists')
    
    for attr in data.attributes:
        if isinstance(attr, AttrDefSchema):
            a: Attribute = db.execute(select(Attribute).where(Attribute.id == attr.attr_id)).scalar()
            if a is None:
                raise Exception(f'Attribute with id {attr.attr_id} does not exist')
        elif isinstance(attr, AttrDefWithAttrDataSchema):
            a = create_attribute(db, attr, commit=False)
            db.flush()

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
                raise Exception('You need to bind foreign key to some schema')
            if attr.bind_to_schema == -1:
                s = sch
            else:
                s = db.execute(select(Schema).where(Schema.id == attr.bind_to_schema)).scalar()
            if s is None:
                raise Exception(f'Cannot bind to nonexistent schema with id {attr.bind_to_schema}')
            bfk = BoundFK(attr_def_id=ad.id, schema_id=s.id)
            db.add(bfk)
    db.commit()
    return sch


def delete_schema(db: Session, schema_id: int) -> Schema:
    schema = db.execute(
        select(Schema)
        .where(Schema.id == schema_id)
        .where(Schema.deleted == False)
    ).scalar()
    if schema is None:
        raise Exception('Schema doesnt exist or was deleted')
    
    db.execute(
        update(Entity).where(Entity.schema_id == schema_id).values(deleted=True)
    )
    schema.deleted = True # TODO require locks?
    db.commit()
    return schema


def update_schema(db: Session, schema_id: int, data: SchemaUpdateSchema) -> Schema:
    sch: Schema = db.execute(select(Schema).where(Schema.id == schema_id)).scalar()
    if sch is None:
        raise Exception(f'Schema with id {schema_id} does not exist')
    
    schemas = db.execute(select(Schema).where( (Schema.name == data.name) | (Schema.slug == data.slug) )).scalars().all()
    if len(schemas) == 1 and schemas[0].id != schema_id or len(schemas) > 1:
        raise Exception(f'Schemas with name {data.name} and/or slug {data.slug} already exist')

    sch.name = data.name
    sch.slug = data.slug
    attr_def_ids: Dict[int, AttributeDefinition] = {i.id: i for i in sch.attr_defs}
    for attr in data.update_attributes:
        attr_def = attr_def_ids.get(attr.id)
        if attr_def is None:
            raise Exception(f'There is no attribute definition with id`{attr.id}` defined for schema')
        if attr_def.list and not attr.list:
            raise Exception('Cannot make listed value unlisted')
        if attr.list:
            attr.unique = False
        attr_def.required = attr.required
        attr_def.unique = attr.unique
        attr_def.list = attr.list
        attr_def.key = attr.key
        attr_def.description = attr.description
    db.flush()
    
    for attr in data.add_attributes:
        if isinstance(attr, AttrDefSchema):
            a: Attribute = db.execute(select(Attribute).where(Attribute.id == attr.attr_id)).scalar()
            if a is None:
                raise Exception(f'Attribute with id {attr.attr_id} does not exist')
        elif isinstance(attr, AttrDefWithAttrDataSchema):
            a = create_attribute(db, attr, commit=False)
            db.flush()
        
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
            raise Exception(f'There is already attribute defined')

        if a.type == AttrType.FK:
            if attr.bind_to_schema is None:
                raise Exception('You need to bind foreign key to some schema')
            if attr.bind_to_schema == -1:
                s = sch
            else:
                s = db.execute(select(Schema).where(Schema.id == attr.bind_to_schema)).scalar()
            if s is None:
                raise Exception(f'Cannot bind to nonexistent schema with id {attr.bind_to_schema}')
            bfk = BoundFK(attr_def_id=ad.id, schema_id=s.id)
            db.add(bfk)
    db.commit()
    return sch
        
        
def create_entity(db: Session, schema_id: int, data: dict) -> Entity:
    sch: Schema = db.execute(select(Schema).where(Schema.id == schema_id)).scalar()
    if sch is None:
        raise Exception(f'Schema with id {schema_id} does not exist')
    e = Entity(schema_id=schema_id)
    db.add(e)
    db.flush()

    for field, value in data.items():
        attr_def: AttributeDefinition = db.execute(
            select(AttributeDefinition)
            .where(AttributeDefinition.schema_id == schema_id)
            .where(Attribute.name == field)
            .join(Attribute, AttributeDefinition.attribute_id == Attribute.id)
        ).scalar()
        if attr_def is None:
            raise Exception(f'There is no attribute definition for schema id {schema_id} and attribute id {attr.id}')
        
        attr: Attribute = attr_def.attribute
        model, caster = attr.type.value
        try:
            if isinstance(value, list):
                if not attr_def.list:
                    raise Exception(f'Attribute {attr.name} on schema {sch.name} cannot hold multiple values')
                values = [caster(i) for i in value]
            else:
                values = [caster(value)]
        except ValueError as e:
            raise # can this even happen with validation done before?
        if attr_def.unique and not attr_def.list:  # TODO this might require a lock
            exists = db.execute(
                select(model)
                .where(model.attribute_id == attr.id)
                .where(Entity.schema_id == schema_id)
                .where(model.value == values[0])
                .join(Entity, Entity.id == model.entity_id)
            ).scalar()
            if exists:
                raise Exception('Non-unique value')
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
        raise Exception('Should we raise exception here?')
    e.deleted = True # TODO require a lock?
    db.commit()
    return e