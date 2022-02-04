from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, subqueryload

from .config import settings
from .crud import ALLOWED_FILTERS
from .database import SessionLocal
from .dynamic_routes import create_dynamic_router
from .models import Schema, AttributeDefinition
from .general_routes import router


def load_schemas(db: Session) -> List[models.Schema]:
    schemas = db.execute(
        select(Schema)
        .options(
            subqueryload(Schema.attr_defs)
        )
    ).scalars().all()
    return schemas


def generate_api_description() -> str:
    description = '# Filters\n\n**Filters list**:'
    for filter, desc in dynamic_routes.FILTER_DESCRIPTION.items():
        description += '\n* `{}` - {}'.format(filter, desc)

    description += '\n\n**Available filters for each type**:'
    for type, filters in ALLOWED_FILTERS.items():
        description += '\n* `{}`: {}'.format(type.name, ', '.join([f'`{i}`' for i in filters]))
    return description


def load_dynamic_routes(db: Session, app: FastAPI):
    schemas = load_schemas(db)
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app)


def create_app(session: Optional[Session] = None) -> FastAPI:
    app = FastAPI(description=generate_api_description())
    origins = ['*']
    app.add_middleware(CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'])

    if session:
        load_dynamic_routes(db=session, app=app)
    else:
        with SessionLocal() as db:
            load_dynamic_routes(db=db, app=app)

    app.include_router(router)
    return app
