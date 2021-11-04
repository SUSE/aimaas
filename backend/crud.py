from typing import Callable, Dict, List, Tuple, Union
from collections import defaultdict

import sqlalchemy
from sqlalchemy import func, distinct, column
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from sqlalchemy.sql.expression import delete, intersect
from sqlalchemy.sql.selectable import CompoundSelect

from .models import (
    AttrType,
    Attribute,
    AttributeDefinition,
    BoundFK,
    Entity,
    Schema,
    Value
)

from .schemas import (
    AttrDefSchema,
    AttrDefWithAttrDataSchema,
    AttributeDefinitionUpdateSchema,
    EntityListSchema,
    SchemaCreateSchema,
    SchemaUpdateSchema,
    AttributeCreateSchema
)
from .exceptions import *


RESERVED_ATTR_NAMES = ['id', 'slug', 'deleted', 'name']
RESERVED_SCHEMA_SLUGS = ['schemas', 'attributes']


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
    if not all:
        q = q.where(Schema.deleted == deleted_only)
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
    if data.slug in RESERVED_SCHEMA_SLUGS:
        raise ReservedSchemaSlugException(slug=data.slug, reserved=RESERVED_SCHEMA_SLUGS)
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


def delete_schema(db: Session, id_or_slug: Union[int, str]) -> Schema:
    q = select(Schema).where(Schema.deleted == False)
    if isinstance(id_or_slug, int):
        q = q.where(Schema.id == id_or_slug)
    else:
        q = q.where(Schema.slug == id_or_slug)
    
    schema = db.execute(q).scalar()
    if schema is None:
        raise MissingSchemaException(obj_id=id_or_slug)
    
    db.execute(
        update(Entity).where(Entity.schema_id == schema.id).values(deleted=True)
    )
    schema.deleted = True
    db.commit()
    return schema


def update_schema(db: Session, id_or_slug: Union[int, str], data: SchemaUpdateSchema) -> Schema:
    if data.slug in RESERVED_SCHEMA_SLUGS:
        raise ReservedSchemaSlugException(slug=data.slug, reserved=RESERVED_SCHEMA_SLUGS)
    
    q = select(Schema).where(Schema.deleted == False)
    if isinstance(id_or_slug, int):
        q = q.where(Schema.id == id_or_slug)
    else:
        q = q.where(Schema.slug == id_or_slug)

    sch: Schema = db.execute(q).scalar()
    if sch is None:
        raise MissingSchemaException(obj_id=id_or_slug)
    
    try:
        db.execute(
            update(Schema)
            .where(Schema.id == sch.id)
            .values(name=data.name, slug=data.slug)
        )
    except sqlalchemy.exc.IntegrityError:
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
        elif a.name in attr_def_names:
            raise AttributeAlreadyDefinedException(attr_id=a.id, schema_id=sch.id)

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
    data = {'id': entity.id, 'slug': entity.slug, 'deleted': entity.deleted, 'name': entity.name}
    for attr in attr_names:
        val_obj = entity.get(attr, db)
        try:
            data[attr] = val_obj.value if not isinstance(val_obj, list) else [i.value for i in val_obj]   
        except AttributeError:
            data[attr] = None
    return data


def _get_attr_values_batch(db: Session, entities: List[Entity], attrs_to_include: List[AttributeDefinition]) -> List[dict]:
    '''Gets attr. values for list of entities by splitting attrs in
    groups by type to select multiple attributes for all entities
    in one query
    '''
    results_map = {
        entity.id: {
            'id': entity.id, 
            'slug': entity.slug, 
            'deleted': entity.deleted, 
            'name': entity.name
        } 
        for entity in entities
    }

    for i in results_map.values():
        for attr_def in attrs_to_include:
            if attr_def.list:
                i.update({attr_def.attribute.name: []})
            else:
                i.update({attr_def.attribute.name: None})

    attr_groups: Dict[str, List[Attribute]] = defaultdict(list)
    attributes = [i.attribute for i in attrs_to_include]
    for attr in attributes:
        attr_groups[attr.type.name].append(attr)
    
    ent_ids = [i.id for i in entities]
    attr_map = {i.attribute.id: i.attribute.name for i in attrs_to_include}
    for group, attrs in attr_groups.items():
        value_model: Value = AttrType[group].value.model
        q = (
            select(value_model)
            .where(value_model.entity_id.in_(ent_ids))
            .where(value_model.attribute_id.in_([i.id for i in attrs]))
        )
        rows = db.execute(q).scalars().all()
        for r in rows:
            ent: dict = results_map[r.entity_id]
            attr: str = attr_map[r.attribute_id]
            if isinstance(ent[attr], list):
                ent[attr].append(r.value)
            else:
                ent[attr] = r.value
    
    results = list(results_map.values())  
    return results


FILTER_MAP = {
    'eq': '__eq__',
    'lt': '__lt__',
    'gt': '__gt__',
    'le': '__le__',
    'ge': '__ge__',
    'ne': '__ne__',
    'contains': 'contains',
    'regexp': 'regexp_match'
}

ALLOWED_FILTERS = {
    AttrType.STR: ['eq', 'lt', 'gt', 'le', 'ge', 'ne', 'contains', 'regexp'],
    AttrType.INT: ['eq', 'lt', 'gt', 'le', 'ge', 'ne'],
    AttrType.FLOAT: ['eq', 'lt', 'gt', 'le', 'ge', 'ne'],
    AttrType.DT: ['eq', 'lt', 'gt', 'le', 'ge', 'ne'],
    AttrType.BOOL: ['eq', 'ne']
}


def _parse_filters(filters: dict, attrs: List[str]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    '''Returns tuple of two `dict`s like `{attr_name: {op1: value, op2: value}}`.
    First `dict` is for attribute filters, second is for `Entity.name` filters
    '''
    attrs_filters = defaultdict(dict)
    name_filters = {}
    for f, v in filters.items():
        split = f.rsplit('.', maxsplit=1)
        attr = split[0]
        filter = 'eq' if len(split) == 1 else split[-1]
        if attr == 'name':
            name_filters[filter] = v
            continue
        elif attr not in attrs:
            raise InvalidFilterAttributeException(attr=attr, allowed_attrs=attrs)
        elif filter not in FILTER_MAP:
            raise InvalidFilterOperatorException(attr=attr, filter=filter)
        attrs_filters[attr][FILTER_MAP[filter]] = v
    
    name_filters = {k: v for k,v in name_filters.items() if k in FILTER_MAP and k in ALLOWED_FILTERS[AttrType.STR]}
    return attrs_filters, name_filters


def _query_entity_with_filters(filters: dict, schema: Schema, all: bool = False, deleted_only: bool = False) -> CompoundSelect:
    '''Returns intersection query of several queries with filters
    to get entities that satisfy all conditions from `filters`
    '''
    
    attrs = {i.attribute.name: i.attribute for i in schema.attr_defs if i.attribute.type in ALLOWED_FILTERS}
    attrs_filters, name_filters = _parse_filters(filters=filters, attrs=list(attrs))
    selects = []

    if name_filters: # since `name` is defined in `Entity`, not in `Value` tables, we need to query it separately
        q = select(Entity).where(Entity.schema_id == schema.id)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
        for f, v in name_filters.items():
            q = q.where(getattr(Entity.name, FILTER_MAP[f])(v))
        selects.append(q)

    for attr_name, filters in attrs_filters.items():
        attr = attrs[attr_name]
        value_model = attr.type.value.model
        q = select(Entity).where(Entity.schema_id == schema.id).join(value_model)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
        for filter, value in filters.items():
            q = q.where(getattr(value_model.value, filter)(value))
        q = q.where(value_model.attribute_id == attr.id)
        selects.append(q)
    return intersect(*selects)


def get_entities(
        db: Session, 
        schema: Schema,
        limit: int = None,
        offset: int = None,
        all: bool = False, 
        deleted_only: bool = False, 
        all_fields: bool = False,
        filters: dict = None
    ) -> EntityListSchema:
    
    if filters:
        q = _query_entity_with_filters(filters=filters, schema=schema, all=all, deleted_only=deleted_only)
    else:
        q = select(Entity).where(Entity.schema_id == schema.id)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
    total = db.execute(select(func.count(distinct(column('id')))).select_from(q.subquery())).scalar()
    q = q.offset(offset).limit(limit).order_by(Entity.id)
    entities = db.execute(select(Entity).from_statement(q)).scalars().all()

    attr_defs = schema.attr_defs if all_fields else [i for i in schema.attr_defs if i.key]
    return EntityListSchema(total=total, entities=_get_attr_values_batch(db, entities, attr_defs))


def get_entity(db: Session, id_or_slug: Union[int, str], schema: Schema) -> dict:
    if isinstance(id_or_slug, int):
        e = db.execute(select(Entity).where(Entity.id == id_or_slug)).scalar()
    else:
        e = db.execute(select(Entity).where(Entity.slug == id_or_slug)).scalar()
    
    if e is None:
        raise MissingEntityException(obj_id=id_or_slug)
    if e.schema_id != schema.id:
        raise MismatchingSchemaException(entity_id=id_or_slug, schema_id=schema.id)

    attrs = [i.attribute.name for i in schema.attr_defs]
    return _get_entity_data(db=db, entity=e, attr_names=attrs)


def _convert_values(attr_def: AttributeDefinition, value: Any, caster: Callable) -> List[Any]:
    if isinstance(value, list):
        if not attr_def.list:
            raise NotListedAttributeException(attr_name=attr_def.attribute.name, schema_id=attr_def.schema_id)
        return [caster(i) for i in value]
    else:
        return [caster(value)]


def _check_fk_value(db: Session, attr_def: AttributeDefinition, entity_ids: List[int]):
    bound_schema_id = db.execute(
        select(BoundFK.schema_id)
        .where(BoundFK.attr_def_id == attr_def.id)
    ).scalar()
    for id_ in entity_ids:
        entity = db.execute(
            select(Entity)
            .where(Entity.id == id_)
            .where(Entity.deleted == False)
        ).scalar()
        if entity is None:
            raise MissingEntityException(obj_id=id_)
        if entity.schema_id != bound_schema_id:
            raise WrongSchemaToBindException(
                attr_name=attr_def.attribute.name, 
                schema_id=attr_def.schema_id, 
                bound_schema_id=bound_schema_id, 
                passed_entity=entity
            )

def _check_unique_value(db: Session, attr_def: AttributeDefinition, model: Value, value: Any):
    existing = db.execute(
        select(model)
        .where(model.attribute_id == attr_def.attribute_id)
        .where(Entity.schema_id == attr_def.schema_id)
        .where(model.value == value)
        .join(Entity, Entity.id == model.entity_id)
    ).scalars().all()
    if existing:
        for val in existing:
            if not val.entity.deleted:
                raise UniqueValueException(attr_name=attr_def.attribute.name, schema_id=attr_def.schema_id, value=val.value)


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
    try:
        name = data.pop('name')
    except KeyError:
        raise RequiredFieldException(field='name')

    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in sch.attr_defs}
    required = [i for i in attr_defs if attr_defs[i].required]
    for i in required:
        if i not in data:
            raise RequiredFieldException(field=i)

    e = Entity(schema_id=schema_id, slug=slug, name=name)
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
        values = _convert_values(attr_def=attr_def, value=value, caster=caster)
        if attr.type == AttrType.FK:
            _check_fk_value(db=db, attr_def=attr_def, entity_ids=values)
        if attr_def.unique and not attr_def.list:
            _check_unique_value(db=db, attr_def=attr_def, model=model, value=values[0])
        for val in values:
            v = model(value=val, entity_id=e.id, attribute_id=attr.id)
            db.add(v)
    db.commit()
    return e


def update_entity(db: Session, id_or_slug: Union[str, int], schema_id: int, data: dict) -> Entity:
    q = select(Entity).where(Entity.schema_id == schema_id)
    q = q.where(Entity.id == id_or_slug) if isinstance(id_or_slug, int) else q.where(Entity.slug == id_or_slug)
    e = db.execute(q).scalar()
    if e is None:
        raise MissingEntityException(obj_id=id_or_slug)
    if e.schema.deleted:
        raise MissingSchemaException(obj_id=e.schema.id)
    
    slug = data.pop('slug', e.slug)
    name = data.pop('name', e.name)
    try:
        db.execute(update(Entity).where(Entity.id == e.id).values(slug=slug, name=name))
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise EntityExistsException(slug=slug)

    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in e.schema.attr_defs}
    for field, value in data.items():
        attr_def = attr_defs.get(field)
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=None, schema_id=schema_id)
        
        attr: Attribute = attr_def.attribute
        model, caster = attr.type.value
        if value is None:
            if attr_def.required:
                raise RequiredFieldException(field=field)
            db.execute(
                delete(model)
                .where(model.entity_id == e.id)
                .where(model.attribute_id == attr_def.attribute_id)
            )
            continue
        
        values = _convert_values(attr_def=attr_def, value=value, caster=caster)
        if attr.type == AttrType.FK:
            _check_fk_value(db=db, attr_def=attr_def, entity_ids=values)
        if attr_def.unique and not attr_def.list:
            _check_unique_value(db=db, attr_def=attr_def, model=model, value=values[0])
        
        db.execute(
            delete(model)
            .where(model.entity_id == e.id)
            .where(model.attribute_id == attr_def.attribute_id)
        )
        for val in values:
            v = model(value=val, entity_id=e.id, attribute_id=attr.id)
            db.add(v)

    db.commit()
    return e


def delete_entity(db: Session, id_or_slug: Union[int, str], schema_id: int) -> Entity:
    q = select(Entity).where(Entity.deleted == False).where(Entity.schema_id == schema_id)
    if isinstance(id_or_slug, int):
        q = q.where(Entity.id == id_or_slug)
    else:
        q = q.where(Entity.slug == id_or_slug)
    e = db.execute(q).scalar()
    if e is None:
        raise MissingEntityException(obj_id=id_or_slug)
    e.deleted = True
    db.commit()
    return e