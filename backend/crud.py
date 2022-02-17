import typing
from typing import Callable, Dict, Tuple
from collections import defaultdict, Counter
from itertools import chain, groupby

from psycopg2.errors import ForeignKeyViolation
from sqlalchemy import func, distinct, column, asc, desc, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql.expression import delete, intersect
from sqlalchemy.sql.selectable import CompoundSelect

from .enum import FilterEnum
from .models import (
    AttrType,
    Attribute,
    AttributeDefinition,
    Schema,
    Value
)

from .schemas import (
    AttrDefSchema,
    EntityListSchema,
    SchemaCreateSchema,
    SchemaUpdateSchema,
    AttributeCreateSchema
)
from .exceptions import *
from .utils import iterate_model_fields


RESERVED_ATTR_NAMES = ['id', 'slug', 'deleted', 'name']


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


def _check_bound_schema_id(db: Session, schema_id: int):
    try:
        db.query(Schema.id).filter(Schema.id == schema_id, Schema.deleted == False).one()
    except NoResultFound:
        raise MissingSchemaException(obj_id=schema_id)


def create_schema(db: Session, data: SchemaCreateSchema, commit: bool = True) -> Schema:
    try:
        sch = Schema(name=data.name, slug=data.slug, reviewable=data.reviewable)
        db.add(sch)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)

    try:
        attr_names = set()
        for attr in data.attributes:
            a = create_attribute(db, attr, commit=False)
            db.flush()

            if a.name in attr_names:
                raise MultipleAttributeOccurencesException(a.name)
            attr_names.add(a.name)

            if a.type == AttrType.FK:
                if attr.bound_schema_id == -1:
                    attr.bound_schema_id = sch.id
                _check_bound_schema_id(db=db, schema_id=attr.bound_schema_id)

            ad = AttributeDefinition(
                attribute_id=a.id,
                schema_id=sch.id,
                required=attr.required,
                list=attr.list,
                unique=attr.unique,
                key=attr.key,
                description=attr.description,
                bound_schema_id=attr.bound_schema_id
            )
            db.add(ad)
            db.flush()
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)
    except:
        db.rollback()
        raise
    return sch


def delete_schema(db: Session, id_or_slug: Union[int, str], commit: bool = True) -> Schema:
    q = select(Schema).where(Schema.deleted == False)
    if isinstance(id_or_slug, int):
        q = q.where(Schema.id == id_or_slug)
    else:
        q = q.where(Schema.slug == id_or_slug)
    
    schema = db.execute(q).scalar()
    if schema is None:
        raise MissingSchemaException(obj_id=id_or_slug)
    
    db.execute(update(Entity)
               .where(Entity.schema_id == schema.id, Entity.deleted == False)
               .values(deleted=True))
    schema.deleted = True
    if commit:
        db.commit()
    else:
        db.flush()
    return schema




def _delete_attr_from_schema(db: Session, attr_def: AttributeDefinition, schema: Schema):
    ValueModel = attr_def.attribute.type.value.model
    db.execute(delete(AttributeDefinition).where(AttributeDefinition.id == attr_def.id))
    db.execute(delete(ValueModel)
        .where(ValueModel.attribute_id == attr_def.attribute_id)
        .where(ValueModel.entity_id == Entity.id)
        .where(Entity.schema_id == schema.id)
        .execution_options(synchronize_session=False)
    )


def _update_attr_in_schema(db: Session, attr_upd: AttrDefSchema, attr_def: AttributeDefinition):
    if attr_def.list and not attr_upd.list:
        raise ListedToUnlistedException(attr_def_id=attr_def.id)

    attr_def.required = attr_upd.required
    attr_def.unique = False if attr_upd.list else attr_upd.unique
    attr_def.list = attr_upd.list
    attr_def.key = attr_upd.key
    attr_def.description = attr_upd.description

    if attr_upd.name != attr_def.attribute.name:
        attr_def.attribute = create_attribute(
            db=db,
            data=AttributeCreateSchema(name=attr_upd.name, type=attr_def.attribute.type.name),
            commit=False
        )


def _add_attr_to_schema(db: Session, attr_schema: AttrDefSchema, schema: Schema):
    attribute = create_attribute(db, attr_schema, commit=False)
    db.flush()
    bound_schema_id = attr_schema.bound_schema_id if attr_schema.bound_schema_id != -1 else schema.id
    if bound_schema_id is not None and bound_schema_id != schema.id:
        _check_bound_schema_id(db=db, schema_id=bound_schema_id)
    try:
        attr_def = AttributeDefinition(
            attribute_id=attribute.id,
            schema_id=schema.id,
            required=attr_schema.required,
            list=attr_schema.list,
            unique=attr_schema.unique if not attr_schema.list else False,
            key=attr_schema.key,
            description=attr_schema.description,
            bound_schema_id=bound_schema_id
        )
        db.add(attr_def)
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if isinstance(error.orig, ForeignKeyViolation):
            raise MissingSchemaException(obj_id=attr_schema.bound_schema_id)
        raise AttributeAlreadyDefinedException(attr_id=attribute.id, schema_id=schema.id)


def sort_attribute_definitions(schema: Schema, definitions: List[AttrDefSchema])\
        -> Tuple[List[AttrDefSchema], List[AttrDefSchema], List[AttributeDefinition]]:
    existing_defs = {x.id: x for x in schema.attr_defs}
    new, updated = [], []
    fields = iterate_model_fields(AttributeDefinition)
    skipped_fields = ["schema_id", "attribute_id", "name", "type", "bound_schema_id"]

    for attr_def in definitions:
        if not getattr(attr_def, "id", None):
            new.append(attr_def)
            continue
        existing = existing_defs.get(attr_def.id, None)
        if existing is None:
            raise AttributeNotDefinedException(attr_id=attr_def.id, schema_id=schema.id)
        if existing.attribute.name != attr_def.name:
            updated.append(attr_def)
        bound_schema_id = attr_def.bound_schema_id if attr_def.bound_schema_id != -1 else existing.bound_schema_id
        if bound_schema_id != existing.bound_schema_id:
            updated.append(attr_def)
            continue
        if any(getattr(attr_def, field) != getattr(existing, field)
               for field in fields
               if field not in skipped_fields):
            updated.append(attr_def)
            continue

    submitted_ids = {a.id for a in definitions}
    deleted = [a for a in existing_defs.values() if a.id not in submitted_ids]
    return new, updated, deleted


def update_schema(db: Session, id_or_slug: Union[int, str], data: SchemaUpdateSchema,
                  commit: bool = True) -> Schema:
    schema = get_schema(db=db, id_or_slug=id_or_slug)
    if schema.deleted:
        raise MissingSchemaException(obj_id=id_or_slug)

    duplicate_attr_names = [name
                            for name, count in Counter(a.name for a in data.attributes).items()
                            if count > 1]
    if duplicate_attr_names:
        raise MultipleAttributeOccurencesException(attr_name=duplicate_attr_names[0])

    try:
        result = db.execute(
            update(Schema)
            .where(Schema.id == schema.id,
                   or_(Schema.name != data.name, Schema.slug != data.slug,
                       Schema.reviewable != (data.reviewable or Schema.reviewable.default.arg)))
            .values(
                name=data.name or schema.name,
                slug=data.slug or schema.slug,
                reviewable=data.reviewable if data.reviewable is not None else schema.reviewable)
        )
    except IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)

    added, updated, deleted = sort_attribute_definitions(schema=schema, definitions=data.attributes)

    # Are there meaningful changes?
    intersect_update_delete = {(d.name, d.type.name) for d in updated} & {(d.attribute.name, d.attribute.type.name) for d in deleted}
    intersect_add_delete = {(d.name, d.type.name) for d in added} & {(d.attribute.name, d.attribute.type.name) for d in deleted}

    if result.rowcount == 0 and intersect_update_delete | intersect_add_delete:
        raise NoOpChangeException("Trivial change: Attempt to add/update and delete an attribute at"
                                  " the same time")

    attr_def_names: Dict[int, AttributeDefinition] = {i.id: i for i in schema.attr_defs}

    for attr_def in deleted:
        _delete_attr_from_schema(db=db, attr_def=attr_def, schema=schema)

    for attr in updated:
        attr_def = attr_def_names.get(attr.id)
        if attr_def is None:
            db.rollback()
            raise AttributeNotDefinedException(attr_id=attr.id, schema_id=schema.id)
        _update_attr_in_schema(db=db, attr_upd=attr, attr_def=attr_def)
    db.flush()

    for attr in added:
        _add_attr_to_schema(db=db, attr_schema=attr, schema=schema)

    try:
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise SchemaExistsException(name=data.name, slug=data.slug)
    return schema


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


def _parse_filters(filters: dict, attrs: List[str]) \
        -> Tuple[Dict[str, Dict[FilterEnum, Any]], Dict[FilterEnum, Any]]:
    '''
    Returns tuple of two `dict`s like `{attr_name: {op1: value, op2: value}}`.
    First `dict` is for attribute filters, second is for `Entity.name` filters
    '''
    filter_map = {f.value.name: f for f in FilterEnum}
    attrs_filters = defaultdict(dict)
    name_filters = {}
    for f, v in filters.items():
        split = f.rsplit('.', maxsplit=1)
        attr = split[0]
        filter = FilterEnum.EQ if len(split) == 1 else filter_map.get(split[-1], None)
        if attr != "name" and attr not in attrs:
            raise InvalidFilterAttributeException(attr=attr, allowed_attrs=attrs)
        if not filter:
            raise InvalidFilterOperatorException(attr=attr, filter=split[-1])

        if attr == 'name':
            name_filters[filter] = v
            continue
        attrs_filters[attr][filter] = v

    return attrs_filters, name_filters


def _query_entity_with_filters(filters: dict, schema: Schema, all: bool = False,
                               deleted_only: bool = False) -> CompoundSelect:
    '''
    Returns intersection query of several queries with filters
    to get entities that satisfy all conditions from `filters`
    '''
    attrs = {i.attribute.name: i.attribute
             for i in schema.attr_defs if i.attribute.type.value.filters}
    attrs_filters, name_filters = _parse_filters(filters=filters, attrs=attrs.keys())
    selects = []

    # since `name` is defined in `Entity`, not in `Value` tables, we need to query it separately
    if name_filters:
        q = select(Entity).where(Entity.schema_id == schema.id)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
        for f, v in name_filters.items():
            q = q.where(getattr(Entity.name, f.value.op)(v))
        selects.append(q)

    for attr_name, filters in attrs_filters.items():
        attr = attrs[attr_name]
        value_model = attr.type.value.model
        q = select(Entity).where(Entity.schema_id == schema.id).join(value_model)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
        for filter, value in filters.items():
            q = q.where(getattr(value_model.value, filter.value.op)(value))
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
        filters: dict = None,
        order_by: str = 'name',
        ascending: bool = True,
    ) -> EntityListSchema:
    if order_by != 'name':
        attrs = [i for i in schema.attr_defs if i.attribute.name == order_by]
        if not attrs:
            raise AttributeNotDefinedException(order_by, schema.id)

    if filters:
        q = _query_entity_with_filters(filters=filters, schema=schema, all=all, deleted_only=deleted_only)
    else:
        q = select(Entity).where(Entity.schema_id == schema.id)
        if not all:
            q = q.where(Entity.deleted == deleted_only)
    total = db.execute(select(func.count(distinct(column('id')))).select_from(q.subquery())).scalar()
    try:
        queries = q.selects
        q1 = queries[0]
        sub = q1.subquery(name='anon_1')
        from_ = Entity.__table__.join(sub, Entity.id == sub.c.id)
        for idx, i in enumerate(queries[1:]):
            sub = i.subquery(name=f'anon_{idx+2}')
            from_ = from_.join(sub, Entity.id == sub.c.id)
        q = select(Entity).select_from(from_)
    except AttributeError:
        pass
    if order_by != 'name':
        attrs = {i.attribute.name: i.attribute for i in schema.attr_defs if i.attribute.type.value.filters}
        attr = attrs[order_by]
        value_model = attr.type.value.model
        direction = asc if ascending else desc
        q = q.order_by(
            direction(
                select(value_model.value)
                .where(value_model.attribute_id == attr.id)
                .where(value_model.entity_id == Entity.id).scalar_subquery()
            ), Entity.name.asc()
        )
    else:
        direction = 'asc' if ascending else 'desc'
        q = q.order_by(getattr(Entity.name, direction)())
    q = q.offset(offset).limit(limit)
    entities = db.execute(select(Entity).from_statement(q)).scalars().all()
    attr_defs = schema.attr_defs if all_fields else [i for i in schema.attr_defs if i.key or i.attribute.name == order_by]
    entities = _get_attr_values_batch(db, entities, attr_defs)
    return EntityListSchema(total=total, entities=entities)


def get_entity_by_id(db: Session, entity_id: int) -> Entity:
    entity = db.execute(select(Entity).where(Entity.id == entity_id)).scalar()
    if entity is None:
        raise MissingEntityException(obj_id=entity_id)
    return entity


def get_entity_model(db: Session, id_or_slug: Union[int, str], schema: Schema) -> Optional[Entity]:
    q = select(Entity).where(Entity.schema_id == schema.id)
    if isinstance(id_or_slug, int):
        return db.execute(q.where(Entity.id == id_or_slug)).scalar()
    else:
        return db.execute(q.where(Entity.slug == id_or_slug)).scalar()


def get_entity(db: Session, id_or_slug: Union[int, str], schema: Schema) -> dict:
    e = get_entity_model(db=db, id_or_slug=id_or_slug, schema=schema)
    
    if e is None:
        raise MissingEntityException(obj_id=id_or_slug)

    attrs = [i.attribute.name for i in schema.attr_defs]
    return _get_entity_data(db=db, entity=e, attr_names=attrs)


def _convert_values(attr_def: AttributeDefinition, value: Any, caster: Callable) -> List[Any]:
    if isinstance(value, list):
        if not attr_def.list:
            raise NotListedAttributeException(attr_name=attr_def.attribute.name, schema_id=attr_def.schema_id)
        return [caster(i) for i in value if i is not None]
    else:
        return [caster(value)] if value is not None else []


def _check_fk_value(db: Session, attr_def: AttributeDefinition, entity_ids: List[int]):
    entities = {e.id: e
                for e in db.query(Entity).filter(Entity.id.in_(entity_ids),
                                                 Entity.deleted == False)}
    for id_ in entity_ids:
        entity = entities.get(id_, None)
        if entity is None:
            raise MissingEntityException(obj_id=id_)
        if entity.schema_id != attr_def.bound_schema_id:
            raise WrongSchemaToBindException(
                attr_name=attr_def.attribute.name, 
                schema_id=attr_def.schema_id, 
                bound_schema_id=attr_def.bound_schema_id,
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


def create_entity(db: Session, schema_id: int, data: dict, commit: bool = True) -> Entity:
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
    except IntegrityError:
        raise EntityExistsException(slug=slug)

    for field, value in data.items():
        attr_def = attr_defs.get(field)
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=None, schema_id=schema_id)

        attr: Attribute = attr_def.attribute
        model, caster, _ = attr.type.value
        values = _convert_values(attr_def=attr_def, value=value, caster=caster)
        if attr.type == AttrType.FK:
            _check_fk_value(db=db, attr_def=attr_def, entity_ids=values)
        if attr_def.unique and not attr_def.list and values:
            _check_unique_value(db=db, attr_def=attr_def, model=model, value=values[0])
        for val in values:
            v = model(value=val, entity_id=e.id, attribute_id=attr.id)
            db.add(v)
    if commit:
        db.commit()
    else:
        db.flush()
    return e


def update_entity(db: Session, id_or_slug: Union[str, int], schema_id: int, data: dict, commit: bool = True) -> Entity:
    q = select(Entity).where(Entity.schema_id == schema_id)
    q = q.where(Entity.id == id_or_slug) if isinstance(id_or_slug, int) else q.where(Entity.slug == id_or_slug)
    e = db.execute(q).scalar()
    if e is None or e.deleted:
        raise MissingEntityException(obj_id=id_or_slug)
    if e.schema.deleted:
        raise MissingSchemaException(obj_id=e.schema.id)
    
    slug = data.pop('slug', e.slug)
    name = data.pop('name', e.name)
    try:
        db.execute(update(Entity).where(Entity.id == e.id).values(slug=slug, name=name))
    except IntegrityError:
        db.rollback()
        raise EntityExistsException(slug=slug)

    attr_defs: Dict[str, AttributeDefinition] = {i.attribute.name: i for i in e.schema.attr_defs}
    for field, value in data.items():
        attr_def = attr_defs.get(field)
        if attr_def is None:
            raise AttributeNotDefinedException(attr_id=None, schema_id=schema_id)
        
        attr: Attribute = attr_def.attribute
        model, caster, _ = attr.type.value
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
        if attr_def.unique and not attr_def.list and values:
            _check_unique_value(db=db, attr_def=attr_def, model=model, value=values[0])
        
        db.execute(
            delete(model)
            .where(model.entity_id == e.id)
            .where(model.attribute_id == attr_def.attribute_id)
        )
        for val in values:
            v = model(value=val, entity_id=e.id, attribute_id=attr.id)
            db.add(v)

    # Ensure that no required attribute remains unset
    non_updated_required_fields = [attr_def for name, attr_def in attr_defs.items()
                                   if attr_def.required and name not in data]
    for model, req_attr_defs in groupby(non_updated_required_fields,
                                        lambda x: x.attribute.type.value[0]):
        expected_attr_ids = {attr_def.attribute_id for attr_def in req_attr_defs}
        present_attr_ids = set(aid[0] for aid in db.query(model.attribute_id)
                                 .filter(model.attribute_id.in_(expected_attr_ids),
                                         model.entity_id == e.id)
                                 .distinct())
        missing_attr_ids = expected_attr_ids - present_attr_ids
        if missing_attr_ids:
            attr_id = next(iter(missing_attr_ids))
            for name, attr_def in attr_defs.items():
                if attr_id == attr_def.attribute_id:
                    raise RequiredFieldException(name)

    if commit:
        db.commit()
    else:
        db.flush()
    return e


def delete_entity(db: Session, id_or_slug: Union[int, str], schema_id: int, commit: bool = True) -> Entity:
    q = select(Entity).where(Entity.deleted == False).where(Entity.schema_id == schema_id)
    if isinstance(id_or_slug, int):
        q = q.where(Entity.id == id_or_slug)
    else:
        q = q.where(Entity.slug == id_or_slug)
    e = db.execute(q).scalar()
    if e is None:
        raise MissingEntityException(obj_id=id_or_slug)
    e.deleted = True
    if commit:
        db.commit()
    else:
        db.flush()
    return e