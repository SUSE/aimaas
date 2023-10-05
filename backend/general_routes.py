from datetime import timedelta
from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_pagination import Params, Page
from sqlalchemy.orm import Session

from .config import settings, VERSION
from . import crud, schemas, exceptions
from .database import get_db
from .enum import FilterEnum
from .models import Schema, AttrType
from .dynamic_routes import create_dynamic_router
from .auth import authenticate_user, authenticated_user, authorized_user, create_access_token,\
    crud as auth_crud
from .auth.enum import PermissionType, RecipientType, PermissionTargetType
from .auth.models import User, Group
from .schemas.auth import (
    GroupSchema, RequirePermission, PermissionSchema,
    UserSchema,
    UserCreateSchema,
    BaseGroupSchema,
    Token
)
from .schemas.info import InfoModel, FilterModel
from .schemas.traceability import ChangeRequestSchema, CountSchema
from .traceability.crud import review_changes, get_pending_change_requests, \
    is_user_authorized_to_review, get_pending_change_request_count
from .traceability.entity import get_recent_entity_changes, entity_change_details
from .traceability.enum import ContentType
from .traceability.schema import create_schema_create_request, create_schema_update_request, \
    create_schema_delete_request, apply_schema_create_request, apply_schema_update_request, \
    apply_schema_delete_request, get_recent_schema_changes, schema_change_details


router = APIRouter()


@router.get("/info", response_model=InfoModel)
def get_info():
    return {
        "version": VERSION,
        "filters": [FilterModel(name=f.value.name, description=f.value.description)
                    for f in FilterEnum],
        "filters_per_type": {atype.name: [filter.value.name for filter in atype.value.filters]
                             for atype in AttrType},
        "help": settings.help
    }


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
    '/schema',
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
    '/schema',
    response_model=schemas.SchemaForListSchema,
    tags=['General routes'],
    summary="Create a schema",
    responses={
            200: {"description": "Schema was created"},
            404: {
                'description': """Can be returned when:
                
                * A schema for foreign key binding does not exist
                * No attribute exists for a given ID 
                """
            },
            409: {"description": """Can be returned when:
                
                * Another schema uses the chosen slug already
                * Duplicate use of attributes
            """},
            410: {"description": "The scheme to bind a foreign key to is deleted"}
        }
)
def create_schema(data: schemas.SchemaCreateSchema, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.CREATE_SCHEMA)))):
    try:
        change_request = create_schema_create_request(db=db, data=data, created_by=user,
                                                      commit=False)
        _, schema = apply_schema_create_request(db=db, change_request=change_request,
                                                reviewed_by=user, comment='Autosubmit')
        db.commit()
        create_dynamic_router(schema=schema, app=request.app)
        return schema
    except exceptions.SchemaExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except (exceptions.MissingAttributeException, exceptions.MissingSchemaException) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.MultipleAttributeOccurencesException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.NoSchemaToBindException as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except exceptions.SchemaIsDeletedException as e:
        raise HTTPException(status.HTTP_410_GONE, str(e))


@router.get(
    '/schema/{id_or_slug}',
    response_model=schemas.SchemaDetailSchema,
    tags=['General routes']
)
def get_schema(id_or_slug: Union[int, str], db: Session = Depends(get_db)):
    try:
        return crud.get_schema(db=db, id_or_slug=id_or_slug)
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.put(
    '/schema/{id_or_slug}',
    response_model=schemas.SchemaBaseSchema,
    tags=['General routes']
)
def update_schema(
        data: schemas.SchemaUpdateSchema,
        id_or_slug: Union[int, str],
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.UPDATE_SCHEMA, target=Schema())))
    ):
    try:
        old_slug = crud.get_schema(db=db, id_or_slug=id_or_slug).slug
        change_request = create_schema_update_request(
            db=db, id_or_slug=id_or_slug, data=data, created_by=user, commit=False
        )
        _, schema = apply_schema_update_request(
            db=db, change_request=change_request, reviewed_by=user, comment='Autosubmit'
        )
        db.commit()
        create_dynamic_router(schema=schema, old_slug=old_slug, app=request.app)
        return schema
    except (exceptions.NoOpChangeException, exceptions.NoSchemaToBindException) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except (exceptions.MissingAttributeException, exceptions.MissingSchemaException,
            exceptions.AttributeNotDefinedException) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except (exceptions.SchemaExistsException, exceptions.ListedToUnlistedException,
             exceptions.MultipleAttributeOccurencesException,
            exceptions.AttributeAlreadyDefinedException,
            exceptions.InvalidAttributeChange) as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


@router.delete(
    '/schema/{id_or_slug}',
    response_model=schemas.SchemaDetailSchema,
    response_model_exclude=['attributes', 'attr_defs'],
    tags=['General routes'],
    summary="Delete schema",
    responses={
        200: {"description": "Schema was deleted"},
        208: {"description": "Schema was already deleted"},
        404: {"description": "Schema does not exist"},
    }
)
def delete_schema(id_or_slug: Union[int, str], db: Session = Depends(get_db),
                  user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.DELETE_SCHEMA)))):
    try:
        change_request = create_schema_delete_request(
            db=db, id_or_slug=id_or_slug, created_by=user, commit=False
        )
        _, schema = apply_schema_delete_request(db=db, change_request=change_request,
                                                reviewed_by=user, comment='Autosubmit')
        db.commit()
        return schema
    except exceptions.NoOpChangeException as e:
        raise HTTPException(status.HTTP_208_ALREADY_REPORTED, str(e))
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.post('/changes/review/{request_id}', tags=["Reviews & Changes"], response_model=ChangeRequestSchema)
def reviewchanges(request_id: int, review: schemas.ChangeReviewSchema, response: Response,
                  db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    try:
        is_user_authorized_to_review(db=db, user=user, request_id=request_id)
        change_request, changed = review_changes(db=db, change_request_id=request_id, review=review,
                                                 reviewed_by=user)
        if not changed:
            response.status_code = status.HTTP_208_ALREADY_REPORTED
        return change_request
    except exceptions.MissingObjectException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/changes/pending/count', tags=["Reviews & Changes"], response_model=CountSchema)
def get_count_pending_changerequests(db: Session = Depends(get_db)):
    return CountSchema(count=get_pending_change_request_count(db=db))


@router.get('/changes/pending', tags=["Reviews & Changes"],
            response_model=Page[schemas.ChangeRequestSchema])
def get_pending_changerequests(
    obj_type: Optional[ContentType] = Query(None),
    db: Session = Depends(get_db),
    params: Params = Depends()
):
    return get_pending_change_requests(obj_type=obj_type, params=params, db=db)


@router.get('/changes/schema/{id_or_slug}', tags=["Reviews & Changes"],
            response_model=Page[schemas.ChangeRequestSchema])
def get_schema_changes(id_or_slug: Union[int, str], params: Params = Depends(),
                              db: Session = Depends(get_db)):
    try:
        schema = crud.get_schema(db=db, id_or_slug=id_or_slug)
        return get_recent_schema_changes(db=db, schema_id=schema.id, params=params)
    except exceptions.MissingSchemaException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/changes/detail/schema/{change_id}', tags=["Reviews & Changes"])
def get_schema_change_details(change_id: int, db: Session = Depends(get_db)):
    try:
        return schema_change_details(db=db, change_request_id=change_id)
    except exceptions.MissingObjectException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get(
    '/changes/entity/{schema_id_or_slug}/{entity_id_or_slug}', tags=["Reviews & Changes"],
    response_model=Page[schemas.ChangeRequestSchema]
)
def get_entity_changes(schema_id_or_slug: Union[int, str], entity_id_or_slug: Union[int, str],
                       db: Session = Depends(get_db), params: Params = Depends()):
    try:
        schema = crud.get_schema(db=db, id_or_slug=schema_id_or_slug)
        entity = crud.get_entity_model(db=db, id_or_slug=entity_id_or_slug, schema=schema)
        return get_recent_entity_changes(db=db, entity_id=entity.id, params=params)
    except exceptions.MissingObjectException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get(
    '/changes/detail/entity/{change_id}', tags=["Reviews & Changes"],
    response_model=schemas.EntityChangeDetailSchema
)
def get_entity_change_details(change_id: int, db: Session = Depends(get_db)):
    try:
        return entity_change_details(db=db, change_request_id=change_id)
    except exceptions.MissingObjectException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/entities/{entity_id}', response_model=schemas.EntityByIdSchema)
def get_entity_by_id(entity_id: int, db: Session = Depends(get_db)):
    return crud.get_entity_by_id(db=db, entity_id=entity_id)


@router.get('/groups', response_model=List[GroupSchema], tags=["Auth"])
def get_groups(db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    return auth_crud.get_groups(db=db)


@router.post('/groups', response_model=GroupSchema, tags=["Auth"])
def create_group(data: BaseGroupSchema, db: Session = Depends(get_db),
                 user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT)))):
    try:
        return auth_crud.create_group(data=data, db=db)
    except exceptions.GroupExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except exceptions.MissingUserException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/groups/{group_id}', response_model=GroupSchema, tags=["Auth"])
def get_group(group_id: int, db: Session = Depends(get_db),
              user: User = Depends(authenticated_user)):
    try:
        return auth_crud.get_group_details(group_id=group_id, db=db)
    except exceptions.MissingGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get('/groups/{group_id}/members', response_model=List[UserSchema], tags=["Auth"])
def get_group_members(group_id: int, db: Session = Depends(get_db),
                      user: User = Depends(authenticated_user)):
    try:
        return auth_crud.get_group_members(group_id=group_id, db=db)
    except exceptions.MissingGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch('/groups/{group_id}/members', response_model=bool, tags=["Auth"],
              summary="Add members to group", responses={
        200: {"description": "Members were added"},
        208: {"description": "Submitted users are already members"}

    })
def add_group_members(group_id: int, new_members: List[int], response: Response,
                      db: Session = Depends(get_db),
                      user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT, target=Group())))):
    try:
        changed = auth_crud.add_members(group_id=group_id, user_ids=new_members,
                                        db=db)
        response.status_code = status.HTTP_200_OK if changed else status.HTTP_208_ALREADY_REPORTED
        return changed
    except exceptions.MissingObjectException as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.delete('/groups/{group_id}/members', response_model=bool, tags=["Auth"],
               summary="Remove members from group", responses={
        200: {"description": "Members were successfully removed"},
        404: {"description": "Group does not exist or users were no members"}
    })
def remove_group_members(group_id: int, members: List[int],
                         db: Session = Depends(get_db),
                         user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT, target=Group())))):
    try:
        return auth_crud.delete_members(group_id=group_id, user_ids=members, db=db)
    except exceptions.MissingObjectException as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.put('/groups/{group_id}', response_model=GroupSchema, tags=["Auth"],
            summary="Update group information", responses={
        200: {"description": "No changes applied to group"},
        201: {"description": "Changes applied to group"}
    })
def update_group(group_id: int, data: BaseGroupSchema, response: Response,
                 db: Session = Depends(get_db),
                 user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT, target=Group())))):
    try:
        group, changed = auth_crud.update_group(group_id=group_id, data=data, db=db)
        response.status_code = status.HTTP_201_CREATED if changed else status.HTTP_200_OK
        return group
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


@router.delete('/groups/{group_id}', response_model=bool, tags=["Auth"], summary="Delete group",
               responses={
                   200: {"description": "Group was deleted"},
                   404: {"description": "Group does not exist"}
               })
def delete_group(group_id: int, db: Session = Depends(get_db),
                 user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT, target=Group())))):
    try:
        return auth_crud.delete_group(group_id=group_id, db=db)
    except exceptions.MissingGroupException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except exceptions.GroupExistsException as e:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"There is at least one subgroup present: {e.name}")


@router.post('/users', response_model=UserSchema, tags=["Auth"])
def create_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    return auth_crud.create_user(db=db, data=user)


@router.get('/users', response_model=List[UserSchema], tags=["Auth"], )
def get_users(db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    return auth_crud.get_users(db=db)


@router.get('/users/{username}/memberships', tags=["Auth"],
            summary="Groups the user is a member of", response_model=List[GroupSchema])
def get_user_groups(username: str, db: Session = Depends(get_db),
                    auser: User = Depends(authenticated_user)) -> List[GroupSchema]:
    user = auth_crud.get_user(username=username, db=db)
    return auth_crud.get_user_groups(user=user, db=db)


@router.patch('/users/{username}', tags=["Auth"], summary="Activate user", responses={
    200: {"description": "User activated"},
    208: {"description": "User is already active"},
    404: {"description": "No such user exists"}
})
def activate_user(username: str, response: Response, db: Session = Depends(get_db),
                  auser: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT)))) -> bool:
    try:
        changed = auth_crud.activate_user(username=username, db=db)
        if not changed:
            response.status_code = status.HTTP_208_ALREADY_REPORTED
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    except exceptions.MissingUserException as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    else:
        return changed


@router.delete('/users/{username}', tags=["Auth"], summary="Deactivate user", responses={
    200: {"description": "User deactivated"},
    208: {"description": "User is already deactivated"},
    404: {"description": "No such user exists"}
})
def deactivate_user(username: str, response: Response, db: Session = Depends(get_db),
                    auser: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT)))) -> bool:
    try:
        changed = auth_crud.deactivate_user(username=username, db=db)
        if not changed:
            response.status_code = status.HTTP_208_ALREADY_REPORTED
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    except exceptions.MissingUserException as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    else:
        return changed


@router.get('/permissions', tags=["Auth"], summary="Get list of granted permissions")
def get_permissions(recipient_type: Optional[RecipientType] = Query(None, description="Type (User or Group) of permission recipient"),
                    recipient_id: Optional[int] = Query(None, description="ID of permission recipient"),
                    obj_type: Optional[PermissionTargetType] = Query(None, description="Type of target object"),
                    obj_id: Optional[int] = Query(None, description="ID of target object"),
                    db: Session = Depends(get_db),
                    user: User = Depends(authenticated_user)):
    try:
        return auth_crud.get_permissions(recipient_type=recipient_type, recipient_id=recipient_id,
                                         obj_type=obj_type, obj_id=obj_id, db=db)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))


@router.post('/permissions', tags=["Auth"], summary="Grant permissions", responses={
    200: {"description": "Permission was granted"},
    208: {"description": "Permission was already granted"}
})
def grant_permissions(data: PermissionSchema, response: Response,
                      db: Session = Depends(get_db),
                      user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT)))) -> bool:
    try:
        changed = auth_crud.grant_permission(data=data, db=db)
        response.status_code = status.HTTP_200_OK if changed else status.HTTP_208_ALREADY_REPORTED
        return changed
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except exceptions.MissingObjectException as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))


@router.delete('/permissions', tags=["Auth"], summary="Revoke permissions", responses={
    200: {"description": "Permissions were revoked"},
    404: {"description": "None of the permissions were revoked"}
})
def revoke_permissions(permission_ids: List[int], response: Response, db: Session = Depends(get_db),
                       user: User = Depends(authorized_user(RequirePermission(permission=PermissionType.USER_MANAGEMENT)))) -> bool:
    changed = auth_crud.revoke_permissions(ids=permission_ids, db=db)
    response.status_code = status.HTTP_200_OK if changed else status.HTTP_404_NOT_FOUND
    return changed


@router.post(settings.token_url, response_model=Token, tags=["Auth"])
async def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token, expiration_date = create_access_token(
        data={'sub': user.username}, expires_delta=timedelta(minutes=settings.token_exp_minutes)
    )
    return {'access_token': access_token, 'token_type': 'bearer',
            'expiration_date': expiration_date}
