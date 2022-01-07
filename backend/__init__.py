from typing import List
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session, subqueryload

from . import database
from .dynamic_routes import create_dynamic_router
from .models import Schema, AttributeDefinition
from .general_routes import router


def load_schemas() -> List[models.Schema]:
    try:
        db: Session = database.SessionLocal()
        schemas = db.execute(
            select(Schema)
            .options(
                subqueryload(Schema.attr_defs)
                .subqueryload(AttributeDefinition.attribute)
            )
        ).scalars().all()
        return schemas
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI()
    origins = ['*']
    app.add_middleware(CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'])
    schemas = load_schemas()
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app, get_db=database.get_db)
    app.include_router(router)

    from . import auth
    from .schemas.auth import Token
    @app.post('/login', response_model=Token)
    async def login(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
        user = auth.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect username or password',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        expires = timedelta(minutes=auth.s.token_exp_minutes)
        access_token = auth.create_access_token(
            data={'sub': user.username}, expires_delta=expires
        )
        return {'access_token': access_token, 'token_type': 'bearer'}
    return app