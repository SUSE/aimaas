from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas, exceptions
from .database import get_db
from .dynamic_routes import create_dynamic_router


router = APIRouter()

@router.get('/attributes', response_model=List[schemas.AttributeSchema])
def get_attributes(db: Session = Depends(get_db)):
    return crud.get_attributes(db)


@router.get('/attributes/{attr_id}', response_model=schemas.AttributeSchema)
def get_attribute(attr_id: int, db: Session = Depends(get_db)):
    try:
        return crud.get_attribute(db=db, attr_id=attr_id)
    except exceptions.MissingAttributeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/schemas', response_model=List[schemas.SchemaForListSchema])
def get_schemas(all: Optional[bool] = False, deleted_only: Optional[bool] = False, db: Session = Depends(get_db)):
    return crud.get_schemas(db=db, all=all, deleted_only=deleted_only)


@router.post('/schemas', response_model=schemas.SchemaForListSchema)
def create_schema(data: schemas.SchemaCreateSchema, db: Session = Depends(get_db)):
    try:
        schema = crud.create_schema(db=db, data=data)
        create_dynamic_router(schema=schema, app=router, get_db=get_db)
        return schema
    except exceptions.SchemaExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.MissingAttributeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MultipleAttributeOccurencesException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.NoSchemaToBindException as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/schemas/{id_or_slug}', response_model=schemas.SchemaDetailSchema)
def get_schema(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
    try:
        return crud.get_schema(db=db, id_or_slug=id_or_slug)
    except exceptions.MissingSchemaException:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.put('/schemas/{id}', response_model=schemas.SchemaDetailSchema)
def update_schema(data: schemas.SchemaUpdateSchema, id: int, db: Session = Depends(get_db)):
    try:
        return crud.update_schema(db=db, schema_id=id, data=data)
    except exceptions.MissingSchemaException:
        pass
    except exceptions.SchemaExistsException:
        pass
    except exceptions.AttributeNotDefinedException:
        pass
    except exceptions.ListedToUnlistedException:
        pass
    except exceptions.MultipleAttributeOccurencesException:
        pass
    except exceptions.AttributeAlreadyDefinedException:
        pass
    except exceptions.NoSchemaToBindException:
        pass
       

