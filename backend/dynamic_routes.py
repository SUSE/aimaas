from typing import List, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.applications import FastAPI
from sqlalchemy.orm.session import Session

from .models import Schema
from . import crud, exceptions


def route_get_entity(router: APIRouter, schema: Schema, get_db: Callable):
    @router.get(
        f'/{schema.slug}/{{entity_id}}',
    )
    def get_entity(entity_id: int, db: Session = Depends(get_db)):
        try:
            return crud.get_entity(db=db, entity_id=entity_id, schema=schema)
        except exceptions.MissingEntityException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        

def route_get_entities(router: APIRouter, schema: Schema, get_db: Callable):
    @router.get(
        f'/{schema.slug}'
    )
    def get_entities(
            limit: int = None, 
            offset: int = None, 
            all: bool = False, 
            deleted_only: bool = False, 
            all_fields: bool = False, 
            db: Session = Depends(get_db)
        ):
        try:
            return crud.get_entities(
                db=db, 
                schema=schema,
                limit=limit,
                offset=offset,
                all=all,
                deleted_only=deleted_only,
                all_fields=all_fields
            )
        except exceptions.MissingSchemaException as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


def route_create_entity(router: APIRouter, schema: Schema, get_db: Callable):
    @router.post(
        f'/{schema.slug}'
    )
    def create_entity(data: dict, db: Session = Depends(get_db)):
        try:
            return crud.create_entity(db=db, schema_id=schema.id, data=data)
        except exceptions.RequiredFieldException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.MissingSchemaException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.AttributeNotDefinedException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.NotListedAttributeException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.MissingEntityException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.WrongSchemaToBindException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        except exceptions.UniqueValueException:
            raise HTTPException(status.HTTP_404_NOT_FOUND)


def create_dynamic_router(schema: Schema, app: FastAPI, get_db: Callable):
    router = APIRouter()
    
    route_get_entity(router=router, schema=schema, get_db=get_db)
    route_get_entities(router=router, schema=schema, get_db=get_db)
    route_create_entity(router=router, schema=schema, get_db=get_db)

    app.include_router(router, prefix='')
    app.openapi_schema = None