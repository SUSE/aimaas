from typing import List

from fastapi import FastAPI
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
    schemas = load_schemas()
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app, get_db=database.get_db)
    app.include_router(router)
    return app