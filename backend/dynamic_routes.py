import logging
from typing import Optional, Union
from dataclasses import make_dataclass

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.applications import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi_pagination import Page, Params
from sqlalchemy.exc import DataError
from sqlalchemy.orm.session import Session

from .auth import authorized_user, authenticated_user
from .auth.enum import PermissionType
from .auth.models import User
from .database import get_db
from .enums import FilterEnum, ModelVariant
from .models import AttrType, Schema, Entity
from .schemas.auth import RequirePermission
from .schemas.entity import EntityModelFactory, EntityBaseSchema
from .schemas.traceability import ChangeRequestSchema
from . import crud, exceptions

from .traceability.entity import create_entity_create_request, create_entity_update_request, \
    create_entity_delete_request, apply_entity_create_request, apply_entity_update_request, \
    apply_entity_delete_request, create_entity_restore_request, apply_entity_restore_request


factory = EntityModelFactory()


def _description_for_get_entity(schema: Schema) -> str:
    description = 'Returns data for all attributes of entity plus fields `id`, `deleted` and `slug`'
    
    fields = [(i.attribute.name, i.required, i.key) for i in schema.attr_defs]
    description += '\n\nFields:'
    for name, expected, key in fields:
        description += f'\n* `{name}` {"" if expected else "(optional)"} {"(key)" if key else ""}'
    return description


def route_get_entity(router: APIRouter, schema: Schema):
    entity_get_schema = factory(schema, ModelVariant.GET)
    description = _description_for_get_entity(schema=schema)

    @router.get(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=entity_get_schema,
        tags=[schema.name],
        summary=f'Get {schema.name} entity by ID',
        description=description,
        response_model_exclude_unset=True,
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
            res = crud.get_entity(db=db, id_or_slug=id_or_slug, schema=schema)
            return res
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

    fields.append(('name', Optional[str], Query(None, description=FilterEnum.EQ.value.description)))
    for filter in AttrType.STR.value.filters:
        fields.append((f'name_{filter.value.name}', Optional[str],
                       Query(None, alias=f'name.{filter.value.name}', description=filter.value.description)))

    for attr_def in schema.attr_defs:
        attr = attr_def.attribute
        if not attr.type.value.filters:
            continue

        type_ = (attr.type  # Attribute.type -> AttrType
            .value.model  # AttrType.value -> Mapping, Mapping.model -> Value model
            .value.property.columns[0].type.python_type)  # get python type of value column in Value child
        # default filter {attr.name} which works as {attr.name}.eq, i.e. for equality filtering
        fields.append((attr.name, Optional[type_],
                       Query(None, alias=attr.name, description=FilterEnum.EQ.value.description)))
        for filter in attr.type.value.filters:
            fields.append((f'{attr.name}_{filter.value.name}', Optional[type_],
                           Query(None, alias=f'{attr.name}.{filter.value.name}',
                                 description=filter.value.description)))

    filter_model = make_dataclass(f"{schema.slug.capitalize().replace('-', '_')}Filters",
                                  fields=fields)
    return filter_model


def route_get_entities(router: APIRouter, schema: Schema):
    description = _description_for_get_entities(schema=schema)
    filter_model = _filters_request_model(schema=schema)

    @router.get(
        f'/{schema.slug}',
        response_model=Page[factory(schema=schema, variant=ModelVariant.GET)],
        tags=[schema.name],
        summary=f'List {schema.name} entities',
        description=description,
        response_model_exclude_unset=True
    )
    def get_entities(
        all: bool = Query(False, description='If true, returns both deleted and not deleted entities'), 
        deleted_only: bool = Query(False, description='If true, returns only deleted entities. *Note:* if `all` is true `deleted_only` is not checked'), 
        all_fields: bool = Query(False, description='If true, returns data for all entity fields, not just key ones'),
        filters: filter_model = Depends(),
        order_by: str = Query('name', description='Ordering field'),
        ascending: bool = Query(True, description='Direction of ordering'),
        db: Session = Depends(get_db),
        params: Params = Depends()
    ):
        filters = {k: v for k, v in filters.__dict__.items() if v is not None}
        new_filters = {}
        for k, v in filters.items():
            split = k.rsplit('_', maxsplit=1)
            attr = split[0]
            filter = split[-1] if len(split) > 1 else 'eq'
            new_filters[f'{attr}.{filter}'] = v
        try:
            return crud.get_entities(
                db=db, 
                schema=schema,
                params=params,
                all=all,
                deleted_only=deleted_only,
                all_fields=all_fields,
                filters=new_filters,
                order_by=order_by,
                ascending=ascending
            )
        # these two exceptions are not supposed to be ever raised
        except exceptions.InvalidFilterAttributeException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except exceptions.InvalidFilterOperatorException as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))


def route_create_entity(router: APIRouter, schema: Schema):
    req_permission = authenticated_user
    if not schema.reviewable:
        req_permission = authorized_user(RequirePermission(
            permission=PermissionType.CREATE_ENTITY,
            target=Schema(id=schema.id)
        ))

    @router.post(
        f'/{schema.slug}',
        response_model=Union[EntityBaseSchema, ChangeRequestSchema],
        tags=[schema.name],
        summary=f'Create new {schema.name} entity',
        responses={
            200: {"description": "Entity was created"},
            202: {"description": "Request to create entity was stored"},
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
    def create_entity(data: factory(schema=schema, variant=ModelVariant.CREATE), response: Response,
                      db: Session = Depends(get_db), user: User = Depends(req_permission)):
        try:
            change_request = create_entity_create_request(
                db=db, schema_id=schema.id, data=data.dict(), created_by=user, commit=False)
            if not schema.reviewable:
                return apply_entity_create_request(db=db, change_request=change_request,
                                                   reviewed_by=user, comment='Autosubmit')[1]
            db.commit()
            response.status_code = status.HTTP_202_ACCEPTED
            return change_request
        except (
                exceptions.MissingSchemaException, exceptions.AttributeNotDefinedException,
                exceptions.MissingEntityException) as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except (exceptions.EntityExistsException, exceptions.UniqueValueException) as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        except (exceptions.NotListedAttributeException, exceptions.WrongSchemaToBindException) as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except DataError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.orig.args[0].strip())


def route_update_entity(router: APIRouter, schema: Schema):
    req_permission = authenticated_user
    if not schema.reviewable:
        req_permission = authorized_user(RequirePermission(
            permission=PermissionType.UPDATE_ENTITY,
            target=Entity()
        ))

    @router.put(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=Union[EntityBaseSchema, ChangeRequestSchema],
        tags=[schema.name],
        summary=f'Update {schema.name} entity',
        responses={
            200: {"description": "Entity was updated"},
            202: {"description": "Request to update entity was stored"},
            208: {"description": "Entity was unchanged because request contained no changes"},
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
            410: {"description": "Entity cannot be updated because it was deleted"},
            422: {
                'description': '''Can be returned when:

                * passed data doesn't follow schema requirements;
                * there were passed multiple values for field that is not defined as listed;
                * entity, passed to FK field, doesn't belong to schema this field is bound to
                '''
            }
        }
    )
    def update_entity(id_or_slug: Union[int, str],
                      data: factory(schema=schema, variant=ModelVariant.UPDATE), response: Response,
                      db: Session = Depends(get_db), user: User = Depends(req_permission)):
        try:
            change_request = create_entity_update_request(
                db=db, id_or_slug=id_or_slug, schema_id=schema.id, created_by=user,
                data=data.dict(exclude_unset=True), commit=False
            )
            if not schema.reviewable:
                return apply_entity_update_request(
                    db=db, change_request=change_request, reviewed_by=user, comment='Autosubmit'
                )[1]
            db.commit()
            response.status_code = status.HTTP_202_ACCEPTED
            return change_request
        except exceptions.NoOpChangeException as e:
            raise HTTPException(status.HTTP_208_ALREADY_REPORTED, str(e))
        except exceptions.EntityIsDeletedException as e:
            raise HTTPException(status.HTTP_410_GONE, str(e))
        except (exceptions.MissingEntityException, exceptions.MissingSchemaException) as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        except (exceptions.EntityExistsException, exceptions.UniqueValueException) as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        except (exceptions.WrongSchemaToBindException, exceptions.RequiredFieldException) as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        except DataError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.orig.args[0].strip())


def route_delete_entity(router: APIRouter, schema: Schema):
    req_permission = authenticated_user
    if not schema.reviewable:
        req_permission = authorized_user(RequirePermission(
            permission=PermissionType.DELETE_ENTITY,
            target=Entity()
        ))

    @router.delete(
        f'/{schema.slug}/{{id_or_slug}}',
        response_model=Union[EntityBaseSchema, ChangeRequestSchema],
        tags=[schema.name],
        summary=f'Delete {schema.name} entity',
        responses={
            200: {"description": "Entity was deleted"},
            202: {"description": "Request to delete entity was stored"},
            208: {"description": "Entity was not changed because request contained no changes"},
            404: {
                'description': "entity with provided id/slug doesn't exist on current schema"
            }
        }
    )
    def delete_entity(id_or_slug: Union[int, str], response: Response,
                      restore: bool = False,
                      db: Session = Depends(get_db),
                      user: User = Depends(req_permission)):
        create_fun, apply_fun = create_entity_delete_request, apply_entity_delete_request
        if restore:
            create_fun, apply_fun = create_entity_restore_request, apply_entity_restore_request

        try:
            change_request = create_fun(
                db=db, id_or_slug=id_or_slug, schema_id=schema.id, created_by=user, commit=False
            )
            if not schema.reviewable:
                return apply_fun(
                    db=db, change_request=change_request, reviewed_by=user, comment='Autosubmit'
                )[1]
            db.commit()
            response.status_code = status.HTTP_202_ACCEPTED
            return change_request
        except exceptions.NoOpChangeException as e:
            raise HTTPException(status.HTTP_208_ALREADY_REPORTED, str(e))
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        

def create_dynamic_router(schema: Schema, app: FastAPI, old_slug: str = None):
    router = APIRouter()
    
    route_get_entities(router=router, schema=schema)
    route_get_entity(router=router, schema=schema)
    route_create_entity(router=router, schema=schema)
    route_update_entity(router=router, schema=schema)
    route_delete_entity(router=router, schema=schema)

    router_routes = [(f"/entity{r.path}", r.methods) for r in router.routes]
    routes_to_remove = []
    for route in app.routes:
        if (route.path, route.methods) in router_routes:
            routes_to_remove.append(route)
        elif old_slug and (route.path.startswith(f'/entity/{old_slug}/') or route.path == f'/entity/{old_slug}'):
            routes_to_remove.append(route)
    for route in routes_to_remove:
        app.routes.remove(route)

    app.include_router(router, prefix='/entity')
