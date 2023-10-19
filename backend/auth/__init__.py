import re
from datetime import datetime, timedelta, timezone
from typing import Optional,  Tuple, Callable

from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.session import Session
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from ..config import settings as s
from .context import pwd_context
from ..database import get_db
from ..models import Schema, Entity
from ..schemas.auth import RequirePermission
from .backends import get
from .crud import get_user, has_permission
from .enum import PermissionType
from .models import User, Group


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=s.token_url, auto_error=True)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    _enabled_backends = get()
    for backend_class in _enabled_backends:
        backend = backend_class(db=db)
        user = backend.authenticate(username=username, password=password)
        if user and user.is_active:
            return user


def create_access_token(data: dict, expires_delta: timedelta) -> Tuple[str, datetime]:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, key=s.secret, algorithm=s.pwd_hash_alg), expire


async def authenticated_user(token: str = Depends(oauth2_scheme),
                             db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, s.secret, algorithms=[s.pwd_hash_alg])
        username = payload.get('sub')
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db=db, username=username)
    if user is None:
        raise credentials_exception
    return user


def authorized_user(required_permission: RequirePermission) -> Callable:
    def schema_slug_from_entity_url(request: Request) -> str:
        match = re.search("/entity/(?P<schema_slug>[^/]+)/", request.url.path)
        if not match:
            raise ValueError("URL does not contain a schema slug")

        return match.group("schema_slug")

    async def is_authorized(request: Request, db: Session = Depends(get_db),
                            user: User = Depends(authenticated_user)) -> User:
        if isinstance(required_permission.target, (Schema, Entity)):
            if not getattr(required_permission.target, "id", None):
                id_or_slug = request.path_params.get("id_or_slug", None)
                if id_or_slug is not None:
                    try:
                        required_permission.target.id = int(id_or_slug)
                    except (ValueError, TypeError):
                        Model = required_permission.target.__class__
                        query = db.query(Model.id).filter(Model.slug == id_or_slug)
                        if isinstance(required_permission.target, Entity):
                            # Caveat, entities in different schemas are allowed th have the same
                            # slug!
                            schema_slug = schema_slug_from_entity_url(request)
                            query = query.join(Schema).filter(Schema.slug == schema_slug)
                        try:
                            required_permission.target.id = query.one()[0]
                        except NoResultFound:
                            required_permission.target = None
                else:
                    required_permission.target = None
            if isinstance(required_permission.target, Entity):
                schema_slug = schema_slug_from_entity_url(request)
                required_permission.target.schema_id = db.query(Schema.id) \
                                                         .filter(Schema.slug == schema_slug) \
                                                         .one()[0]
        elif isinstance(required_permission.target, Group):
            group_id = request.path_params.get("group_id", None)
            required_permission.target.id = int(group_id)
        elif required_permission.target is not None:
            raise TypeError(f"Permission management for type {type(required_permission.target)} "
                            f"not supported")
        hp = has_permission(user=user, permission=required_permission, db=db)
        if not hp:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="You are not authorized for this action"
            )
        return user

    return is_authorized
