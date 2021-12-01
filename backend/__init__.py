from typing import List
# from datetime import timedelta

from fastapi import FastAPI#, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session, subqueryload

from . import database, crud, dynamic_routes
from .dynamic_routes import create_dynamic_router
from .models import Schema, AttributeDefinition, BoundFK



def load_schemas() -> List[models.Schema]:
    try:
        db: Session = database.SessionLocal()
        schemas = db.execute(
            select(Schema)
            .options(
                subqueryload(Schema.attr_defs)
                .subqueryload(AttributeDefinition.attribute)
            )
             .options(
                subqueryload(Schema.attr_defs)
                .subqueryload(AttributeDefinition.bound_fk)
                .subqueryload(BoundFK.schema)
            )
        ).scalars().all()
        return schemas
    finally:
        db.close()


def generate_api_description() -> str:
    description = '# Filters\n\n**Filters list**:'
    for filter, desc in dynamic_routes.FILTER_DESCRIPTION.items():
        description += '\n* `{}` - {}'.format(filter, desc)

    description += '\n\n**Available filters for each type**:'
    for type, filters in crud.ALLOWED_FILTERS.items():
        description += '\n* `{}`: {}'.format(type.name, ', '.join([f'`{i}`' for i in filters]))
    return description


def create_app() -> FastAPI:
    from .general_routes import router
    
    app = FastAPI(description=generate_api_description())
    schemas = load_schemas()
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app, get_db=database.get_db)
    app.include_router(router)

    origins = ['*']
    app.add_middleware(CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'])

    # from . import auth
    # @app.post("/token", response_model=auth.Token)
    # async def login_for_access_token(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    #     user = auth.authenticate_user(db, form_data.username, form_data.password)
    #     if not user:
    #         raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Incorrect username or password",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )
    #     access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    #     access_token = auth.create_access_token(
    #         data={"sub": user.username}, expires_delta=access_token_expires
    #     )
    #     return {"access_token": access_token, "token_type": "bearer"}
    return app