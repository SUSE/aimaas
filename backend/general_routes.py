from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from . import crud, schemas, exceptions
from .database import get_db
from .dynamic_routes import create_dynamic_router


router = APIRouter()

@router.get(
    '/attributes', 
    response_model=List[schemas.AttributeSchema],
    tags=['General routes']
)
def get_attributes(db: Session = Depends(get_db)):
    return crud.get_attributes(db)


@router.get(
    '/attributes/{attr_id}', 
    response_model=schemas.AttributeSchema,
    tags=['General routes']
)
def get_attribute(attr_id: int, db: Session = Depends(get_db)):
    try:
        return crud.get_attribute(db=db, attr_id=attr_id)
    except exceptions.MissingAttributeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get(
    '/schemas', 
    response_model=List[schemas.SchemaForListSchema],
    tags=['General routes']
)
def get_schemas(
    all: Optional[bool] = Query(False, description='If true, returns both deleted and not deleted schemas'), 
    deleted_only: Optional[bool] = Query(False, description='If true, returns only deleted entities. *Note:* if `all` is true `deleted_only` is not checked'), 
    db: Session = Depends(get_db)
):
    return crud.get_schemas(db=db, all=all, deleted_only=deleted_only)


@router.post(
    '/schemas', 
    response_model=Union[schemas.SchemaForListSchema, dict],
    tags=['General routes']
)
def create_schema(data: schemas.SchemaCreateSchema, request: Request, db: Session = Depends(get_db)):
    try:
        from sqlalchemy import select
        user = db.execute(select(User)).scalar()
        change = traceability.create_schema_create_request(
            db=db, data=data, created_by=user, commit=False
        )
        schema =  traceability.apply_schema_create_request(db=db, change_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        create_dynamic_router(schema=schema, app=request.app, get_db=get_db)
        return schema
    except exceptions.ReservedSchemaSlugException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
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


@router.get(
    '/schemas/{id_or_slug}', 
    response_model=schemas.SchemaDetailSchema,
    tags=['General routes']
)
def get_schema(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
    try:
        return crud.get_schema(db=db, id_or_slug=id_or_slug)
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.put(
    '/schemas/{id_or_slug}', 
    response_model=schemas.SchemaBaseSchema,
    tags=['General routes']
)
def update_schema(
    data: schemas.SchemaUpdateSchema, 
    id_or_slug: Union[int, str], 
    request: Request, 
    db: Session = Depends(get_db),
    ):
    try:
        old_slug = crud.get_schema(db=db, id_or_slug=id_or_slug).slug

        from sqlalchemy import select
        user = db.execute(select(User)).scalar()
        change = traceability.create_schema_update_request(
            db=db, id_or_slug=id_or_slug, data=data, created_by=user, commit=False
        )
        schema =  traceability.apply_schema_update_request(db=db, change_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        create_dynamic_router(schema=schema, old_slug=old_slug, app=request.app, get_db=get_db)
        return schema
    except exceptions.ReservedSchemaSlugException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.MissingAttributeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.SchemaExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.AttributeNotDefinedException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.ListedToUnlistedException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.MultipleAttributeOccurencesException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.AttributeAlreadyDefinedException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.NoSchemaToBindException as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))


@router.delete(
    '/schemas/{id_or_slug}', 
    response_model=schemas.SchemaDetailSchema,
    response_model_exclude=['attributes', 'attr_defs'],
    tags=['General routes']
)
def delete_schema(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
    try:
        from sqlalchemy import select
        user = db.execute(select(User)).scalar()
        change = traceability.create_schema_delete_request(
            db=db, id_or_slug=id_or_slug, created_by=user, commit=False
        )
        schema = traceability.apply_schema_delete_request(db=db, change_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        return schema
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))