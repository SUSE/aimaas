from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from . import crud, schemas, exceptions, auth
from .database import get_db
from .models import PermObject, PermType, User
from .dynamic_routes import create_dynamic_router
# from .auth import get_current_user, is_authorized
from .schemas.auth import (
    GroupSchema,
    GroupDetailsSchema,
    UserSchema,
    UserCreateSchema,
    CreateGroupSchema,
    UpdateGroupSchema
)


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
    response_model=schemas.SchemaForListSchema,
    tags=['General routes']
)
def create_schema(data: schemas.SchemaCreateSchema, request: Request, db: Session = Depends(get_db)):
    try:
        schema = crud.create_schema(db=db, data=data)
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
    response_model=schemas.SchemaDetailSchema,
    tags=['General routes']
)
def update_schema(data: schemas.SchemaUpdateSchema, id_or_slug: Union[int, str], request: Request, db: Session = Depends(get_db)):
    try:
        old_slug = crud.get_schema(db=db, id_or_slug=id_or_slug).slug
        schema = crud.update_schema(db=db, id_or_slug=id_or_slug, data=data)
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
        return crud.delete_schema(db=db, id_or_slug=id_or_slug)
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/groups', response_model=List[GroupSchema])
def get_groups(db: Session = Depends(get_db)):
    return auth.get_groups(db=db)


@router.post('/groups', response_model=GroupSchema)
def create_group(data: CreateGroupSchema, db: Session = Depends(get_db)):
    try:
        return auth.create_group(data=data, db=db)
    except exceptions.GroupExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.MissingUserException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/groups/{group_id}', response_model=GroupDetailsSchema)
def get_group(group_id: int, db: Session = Depends(get_db)):
    try:
        return auth.get_group_details(group_id=group_id, db=db)
    except exceptions.MissingGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/groups/{group_id}/members', response_model=List[UserSchema])
def get_group_members(group_id: int, db: Session = Depends(get_db)):
    try:
        return auth.get_group_members(group_id=group_id, db=db)
    except exceptions.MissingGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.put('/groups/{group_id}', response_model=GroupSchema)
def update_group(group_id: int, data: UpdateGroupSchema, db: Session = Depends(get_db)):
    try:
        return auth.update_group(group_id=group_id, data=data, db=db)
    except exceptions.CircularGroupReferenceException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.GroupExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.NoOpChangeException as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except exceptions.MissingPermissionException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingGroupPermissionException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingUserException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingUserGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.post('/users', response_model=auth.UserSchema)
def create_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    user_ = User(email=user.email, username=user.username, password=auth.get_password_hash(user.password))
    db.add(user_)
    db.commit()
    return user_


@router.get('/users', response_model=List[UserSchema])
def get_users(db: Session = Depends(get_db)):
    return auth.get_users(db=db)
