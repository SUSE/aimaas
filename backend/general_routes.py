from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import select

from backend.models import ContentType, PermObject, PermType, User
from backend.schemas.entity import EntityBaseSchema
from backend.schemas.schema import SchemaBaseSchema
from backend.schemas.traceability import ChangeRequestSchema, SchemaChangeRequestSchema

from . import crud, schemas, exceptions, traceability, auth
from .database import get_db
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
        schema =  traceability.apply_schema_create_request(db=db, change_request_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        create_dynamic_router(schema=schema, app=request.app, get_db=get_db)
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
        schema =  traceability.apply_schema_update_request(db=db, change_request_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        create_dynamic_router(schema=schema, old_slug=old_slug, app=request.app, get_db=get_db)
        return schema
    except exceptions.NoOpChangeException as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
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
        schema = traceability.apply_schema_delete_request(db=db, change_request_id=change.id, reviewed_by=user, comment='Autosubmit')
        db.commit()
        return schema
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        

@router.post('/changes/review/{id}', response_model=Union[
    ChangeRequestSchema, SchemaBaseSchema, EntityBaseSchema
])
def review_changes(id: int, review: schemas.ChangeReviewSchema, db: Session = Depends(get_db)):
    # user: User = Depends(get_current_user), 
    user = db.execute(select(User)).scalar()
    try:
        return traceability.review_changes(db=db, change_request_id=id, review=review, reviewed_by=user)
    except (
        exceptions.MissingChangeException,
        exceptions.MissingSchemaCreateRequestException,
        exceptions.MissingSchemaUpdateRequestException,
        exceptions.MissingSchemaDeleteRequestException,
        exceptions.MissingEntityCreateRequestException,
        exceptions.MissingEntityUpdateRequestException,
        exceptions.MissingEntityDeleteRequestException
    ) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/changes/pending', response_model=List[schemas.ChangeRequestSchema])
def get_pending_change_requests(
    obj_type: Optional[ContentType] = Query(None),
    limit: Optional[int] = Query(10),
    offset: Optional[int] = Query(0),
    all: Optional[bool] = Query(False),
    db: Session = Depends(get_db)
):
    return traceability.get_pending_change_requests(obj_type=obj_type, limit=limit, offset=offset, all=all, db=db)


@router.get('/changes/schema/{id_or_slug}', response_model=schemas.SchemaChangeRequestSchema)
def get_recent_schema_changes(id_or_slug: Union[int, str], count: Optional[int] = Query(5), db: Session = Depends(get_db)):
    try:
        schema = crud.get_schema(db=db, id_or_slug=id_or_slug)
        schema_changes, pending_entity_requests = traceability.get_recent_schema_changes(db=db, schema_id=schema.id, count=count)
        return SchemaChangeRequestSchema(schema_changes=schema_changes, pending_entity_requests=pending_entity_requests)
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/changes/detail/schema/{change_id}')
def get_schema_change_details(change_id: int, db: Session = Depends(get_db)):
    try:
        return traceability.schema_change_details(db=db, change_request_id=change_id)
    except exceptions.MissingChangeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get(
    '/changes/entity/{schema_id_or_slug}/{entity_id_or_slug}',
    response_model=List[schemas.ChangeRequestSchema]
)
def get_recent_entity_changes(schema_id_or_slug: Union[int, str], entity_id_or_slug: Union[int, str], count: Optional[int] = Query(5), db: Session = Depends(get_db)):
    try:
        schema = crud.get_schema(db=db, id_or_slug=schema_id_or_slug)
        entity = crud.get_entity_model(db=db, id_or_slug=entity_id_or_slug, schema=schema)
        if entity is None:
            raise exceptions.MissingEntityException(obj_id=entity_id_or_slug)
        return traceability.get_recent_entity_changes(db=db, entity_id=entity.id, count=count)
    except exceptions.MissingEntityException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get(
    '/changes/detail/entity/{change_id}',
    response_model=schemas.EntityChangeDetailSchema
)
def get_entity_change_details(change_id: int, db: Session = Depends(get_db)):
    try:
        return traceability.entity_change_details(db=db, change_request_id=change_id)
    except exceptions.MissingChangeException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingEntityException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/entities/{entity_id}', response_model=schemas.EntityByIdSchema)
def get_entity_by_id(entity_id: int, db: Session = Depends(get_db)):
    return crud.get_entity_by_id(db=db, entity_id=entity_id)


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

