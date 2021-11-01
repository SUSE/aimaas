from typing import List, Callable, Optional, Union
from dataclasses import make_dataclass

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.applications import FastAPI
from sqlalchemy.orm.session import Session
from pydantic import create_model, Field, validator
from pydantic.main import ModelMetaclass

from .models import AttrType, Schema, AttributeDefinition
from . import crud, exceptions, schemas


def _make_type(attr_def: AttributeDefinition, optional: bool = False) -> tuple:
    '''Given `AttributeDefinition` returns a type that will be for type annotations in Pydantic model'''
    
    type_ = (attr_def.attribute.type  # AttributeDefinition.Attribute.type -> AttrType
            .value.model  # AttrType.value -> Mapping, Mapping.model -> Value model
            .value.property.columns[0].type.python_type)  # get python type of value column in Value child
    if attr_def.list:
        type_ = List[type_]
    if not attr_def.required or optional:
        type_ = Optional[type_]
    return (type_, Field(description=attr_def.description))


def _get_entity_request_model(schema: Schema, name: str) -> ModelMetaclass:
    '''
    Creates Pydantic entity get model

    Model includes all entity attributes, which are all marked as `Optional`,
    and their descriptions, if defined in `AttributeDefinition`.
    Also includes fields `id`, `slug`, `name` and `deleted`.

    Why attributes are `Optional`: currently, if we add new requried
    field to schema, which already holds some entities, values for this
    field in these entities will be `None` and if we don't mark fields
    as `Optional`, Pydantic will raise exception after receiving `None`
    for required field.

    So make it clear, which fields are not `Optional` and expected to be
    in response in any case, it is advised to provide documentation
    in API that will list all fields and mark them as required/optional.
    '''
    field_names = [i.attribute.name for i in schema.attr_defs]
    types = [_make_type(i, optional=True) for i in schema.attr_defs]
    fields_types = dict(zip(field_names, types))

    default_fields = {
        'id': (int, Field(description='ID of this entity')),
        'deleted': (bool, Field(description='Indicates whether this entity is marked as deleted')),
        'slug': (str, Field(description='Slug for this entity')),
        'name': (str, Field(description='Name of this entity'))
    }
    model = create_model(
        name,
        **fields_types,
        **default_fields
    )
    return model


def _description_for_get_entity(schema: Schema) -> str:
    description = 'Returns data for all attributes of entity plus fields `id`, `deleted` and `slug`'
    
    fields = [(i.attribute.name, i.required, i.key) for i in schema.attr_defs]
    description += '\n\nFields:'
    for name, expected, key in fields:
        description += f'\n* `{name}` {"" if expected else "(optional)"} {"(key)" if key else ""}'
    return description


def route_get_entity(router: APIRouter, schema: Schema, get_db: Callable):
    entity_get_schema = _get_entity_request_model(schema=schema, name=f"{schema.slug.capitalize().replace('-', '_')}Get") 
    description = _description_for_get_entity(schema=schema)

    @router.get(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=entity_get_schema,
        tags=[schema.name],
        summary=f'Get {schema.name} entity by ID',
        description=description,
        responses={
            404: {
                'description': "Entity with provided ID doesn't exist",
            },
            409: {
                'description': "Entity with provided ID doesn't belong to current schema"
            }
        }
    )
    def get_entity(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
        try:
            return crud.get_entity(db=db, id_or_slug=id_or_slug, schema=schema)
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.MismatchingSchemaException as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))


def _description_for_get_entities(schema: Schema) -> str:
    description = 'Lists entities from schema. By default returns *all not deleted* entities with data *only for key fields*'
    key_fields = [(i.attribute.name, i.required) for i in schema.attr_defs if i.key]
    key_fields_description = '\n\nKey fields:'
    for name, expected in key_fields:
        key_fields_description += f'\n* `{name}` {"" if expected else "(optional)"}'
    
    other_fields = [(i.attribute.name, i.required) for i in schema.attr_defs if not i.key]
    other_fields_description = '\n\nOther fields:'
    for name, expected in other_fields:
        other_fields_description += f'\n* `{name}` {"" if expected else "(optional)"}'
    
    description += key_fields_description
    description += other_fields_description
    return description


def _filters_request_model(schema: Schema):
    '''Creates a dataclass that will be used to
    capture filters like `<attr_name>.<operator>=<value>`
    in entity listing queries
    '''
    fields = []

    fields.append(('name', Optional[str], Query(None)))
    for filter in crud.ALLOWED_FILTERS[AttrType.STR]:
        fields.append((f'name_{filter}', Optional[str], Query(None, alias=f'name.{filter}')))

    for attr_def in schema.attr_defs:
        attr = attr_def.attribute
        if attr.type not in crud.ALLOWED_FILTERS or attr_def.list:
            continue

        type_ = (attr.type  # Attribute.type -> AttrType
            .value.model  # AttrType.value -> Mapping, Mapping.model -> Value model
            .value.property.columns[0].type.python_type)  # get python type of value column in Value child
        # default filter {attr.name} which works as {attr.name}.eq, i.e. for equality filtering
        fields.append((attr.name, Optional[type_], Query(None, alias=attr.name)))
        for filter in crud.ALLOWED_FILTERS[attr.type]:
            fields.append((f'{attr.name}_{filter}', Optional[type_], Query(None, alias=f'{attr.name}.{filter}')))

    filter_model = make_dataclass(f"{schema.slug.capitalize().replace('-', '_')}Filters", fields=fields)
    return filter_model


def route_get_entities(router: APIRouter, schema: Schema, get_db: Callable):
    entity_schema = _get_entity_request_model(schema=schema, name=f"{schema.slug.capitalize().replace('-', '_')}ListItem")
    description = _description_for_get_entities(schema=schema)
    filter_model = _filters_request_model(schema=schema)
    response_model = create_model(
        f'Get{entity_schema.__name__}', 
        total=(int, Field(description='Total number of entities satisfying conditions')),
        entities=(List[entity_schema], Field(description='List of returned entities'))
    )
    @router.get(
        f'/{schema.slug}',
        response_model=response_model,
        tags=[schema.name],
        summary=f'List {schema.name} entities',
        description=description,
        response_model_exclude_unset=True
    )
    def get_entities(
        limit: int = Query(None, min=0, description='Limit results to `limit` entities'), 
        offset: int = Query(None, min=0, description='Take an offset of `offset` when retreiving entities'), 
        all: bool = Query(False, description='If true, returns both deleted and not deleted entities'), 
        deleted_only: bool = Query(False, description='If true, returns only deleted entities. *Note:* if `all` is true `deleted_only` is not checked'), 
        all_fields: bool = Query(False, description='If true, returns data for all entity fields, not just key ones'), 
        filters: filter_model = Depends(),
        db: Session = Depends(get_db)
    ):
        filters = {k: v for k, v in filters.__dict__.items() if v is not None}
        new_filters = {}
        for k, v in filters.items():
            split = k.split('_')
            attr = '_'.join(split[:-1]) if len(split) > 1 else split[0]
            filter = split[-1] if len(split) > 1 else 'eq'
            new_filters[f'{attr}.{filter}'] = v

        return crud.get_entities(
            db=db, 
            schema=schema,
            limit=limit,
            offset=offset,
            all=all,
            deleted_only=deleted_only,
            all_fields=all_fields,
            filters=new_filters
        )
       

def _create_entity_request_model(schema: Schema) -> ModelMetaclass:
    '''
    Creates Pydantic entity create model

    Model includes all entity attributes, which are marked as `Optional`
    if defined so in `AttributeDefinition`,
    plus required `slug` field with custom validator for it and required
    `name` field.

    This model will raise exception if passed fields that don't
    belong to it.
    '''
    field_names = [i.attribute.name for i in schema.attr_defs]
    types = [_make_type(i) for i in schema.attr_defs]
    fields_types = dict(zip(field_names, types))
    
    class Config:
        extra = 'forbid'

    model = create_model(
        f"{schema.slug.capitalize().replace('-', '_')}Create",
        **fields_types,
        slug=(str, Field(description='Slug of this entity')),
        name=(str, Field(description='Name of this entity')),
        __config__=Config,
        __validators__={'slug_validator': validator('slug', allow_reuse=True)(schemas.validate_slug)}
    )
    return model


def route_create_entity(router: APIRouter, schema: Schema, get_db: Callable):
    entity_create_schema = _create_entity_request_model(schema=schema)
    @router.post(
        f'/{schema.slug}',
        response_model=schemas.EntityBaseSchema,
        tags=[schema.name],
        summary=f'Create new {schema.name} entity',
        responses={
            404: {
                'description': '''Can be returned when:

                * schema, this new entity belongs to, doesn't exist or is deleted;
                * passed attribute doesn't exist on current schema;
                * entity passed in FK field doesn't exist.
                '''
            },
            409: {
                'description': '''Can be returned when:

                * entity with provided slug already exists on current schema;
                * there already exists an entity that has same value for unique field and this entity is not deleted.
                '''
            },
            422: {
                'description': '''Can be returned when:

                * passed data doesn't follow schema requirements;
                * entity, passed to FK field, doesn't belong to schema this field is bound to.
                '''
            }
        }
    )
    def create_entity(data: entity_create_schema, db: Session = Depends(get_db)):
        try:
            return crud.create_entity(db=db, schema_id=schema.id, data=data.dict())
        except exceptions.MissingSchemaException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.EntityExistsException as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        except exceptions.AttributeNotDefinedException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.NotListedAttributeException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.WrongSchemaToBindException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except exceptions.UniqueValueException as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))


def _update_entity_request_model(schema: Schema) -> ModelMetaclass:
    '''
    Creates Pydantic entity update model

    Model includes all entity attributes as `Optional` fields,
    with descriptions taken from `AttributeDefinition`,
    plus `Optional` `slug` field with custom validator for it
    and `Optional` `name` field.

    This model will raise exception if passed fields that don't
    belong to it.
    '''
    field_names = [i.attribute.name for i in schema.attr_defs]
    types = [_make_type(i, optional=True) for i in schema.attr_defs]
    fields_types = dict(zip(field_names, types))
    
    class Config:
        extra = 'forbid'
    
    model = create_model(
        f"{schema.slug.capitalize().replace('-', '_')}Update",
        **fields_types,
        slug=(Optional[str], Field(description='Slug of this entity')),
        name=(Optional[str], Field(description='Name of this entity')),
        __config__=Config,
        __validators__={'slug_validator': validator('slug', allow_reuse=True)(schemas.validate_slug)}
    )
    return model


def route_update_entity(router: APIRouter, schema: Schema, get_db: Callable):
    entity_update_schema = _update_entity_request_model(schema=schema)
    @router.put(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=schemas.EntityBaseSchema,
        tags=[schema.name],
        summary=f'Update {schema.name} entity',
        responses={
            404: {
                'description': '''Can be returned when:

                * entity with provided id/slug doesn't exist on current schema;
                * schema, this entity belongs to, is deleted;
                * passed attribute doesn't exist on current schema;
                * schema, this new entity belongs to, doesn't exist or is deleted;
                * entity passed in FK field doesn't exist.
                '''
            },
            409: {
                'description': '''Can be returned when:
                
                * entity with provided slug already exists on current schema;
                * there already exists an entity that has same value for unique field and this entity is not deleted
                '''
            },
            422: {
                'description': '''Can be returned when:

                * passed data doesn't follow schema requirements;
                * there were passed multiple values for field that is not defined as listed;
                * entity, passed to FK field, doesn't belong to schema this field is bound to
                '''
            }
        }
    )
    def update_entity(id_or_slug: Union[int, str], data: entity_update_schema, db: Session = Depends(get_db)):
        try:
            return crud.update_entity(db=db, id_or_slug=id_or_slug, schema_id=schema.id, data=data.dict(exclude_unset=True))
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.MissingSchemaException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except exceptions.EntityExistsException as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        except exceptions.WrongSchemaToBindException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except exceptions.UniqueValueException as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        except exceptions.RequiredFieldException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) 


def route_delete_entity(router: APIRouter, schema: Schema, get_db: Callable):
    @router.delete(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=schemas.EntityBaseSchema,
        tags=[schema.name],
        summary=f'Delete {schema.name} entity',
        responses={
            404: {
                'description': "entity with provided id/slug doesn't exist on current schema"
            }
        }
    )
    def delete_entity(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
        try:
            return crud.delete_entity(db=db, id_or_slug=id_or_slug, schema_id=schema.id)
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        

def create_dynamic_router(schema: Schema, app: FastAPI, get_db: Callable, old_slug: str = None):
    router = APIRouter()
    
    route_get_entities(router=router, schema=schema, get_db=get_db)
    route_get_entity(router=router, schema=schema, get_db=get_db)
    route_create_entity(router=router, schema=schema, get_db=get_db)
    route_update_entity(router=router, schema=schema, get_db=get_db)
    route_delete_entity(router=router, schema=schema, get_db=get_db)

    router_routes = [(r.path, r.methods) for r in router.routes]
    routes_to_remove = []
    for route in app.routes:
        if (route.path, route.methods) in router_routes:
            routes_to_remove.append(route)
        elif old_slug and (route.path.startswith(f'/{old_slug}/') or route.path == f'/{old_slug}'):
            routes_to_remove.append(route)
    for route in routes_to_remove:
        app.routes.remove(route)

    app.include_router(router, prefix='')
    app.openapi_schema = None