import threading
from contextlib import asynccontextmanager
from typing import List, Optional

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, subqueryload

from .config import settings
from .database import SessionLocal
from .dynamic_routes import create_dynamic_router
from .enums import FilterEnum
from .general_routes import router
from .models import Schema, AttributeDefinition, AttrType


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
    for filter in FilterEnum:
        description += '\n* `{}` - {}'.format(filter.value.name, filter.value.description)

    description += '\n\n**Available filters for each type**:'
    for atype in AttrType:
        description += '\n* `{}`: {}'.format(atype.name, ', '.join([f'`{i.value.name}`' for i in atype.value.filters]))
    return description


def load_dynamic_routes(db: Session, app: FastAPI):
    schemas = load_schemas(db)
    for schema in schemas:
        create_dynamic_router(schema=schema, app=app)


"""
POSTGRES LISTEN/NOTIFY

SQL script to create triggers
==============================

-- Create a trigger function to handle insert and update events
CREATE OR REPLACE FUNCTION notify_changes()
RETURNS TRIGGER AS $$
BEGIN
-- Notify listening clients about the change
   	NOTIFY schema_changes;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
-- Create a trigger for insert events
CREATE TRIGGER schema_insert_trigger
AFTER INSERT ON schemas
FOR EACH ROW
EXECUTE FUNCTION notify_changes();

-- Create a trigger for update events
CREATE TRIGGER schema_update_trigger
AFTER UPDATE ON schemas
FOR EACH ROW
EXECUTE FUNCTION notify_changes();

==============================
"""


class Watcher(threading.Thread):

    def __init__(self, app_reference):
        super().__init__()
        self.app_reference = app_reference

    def run(self):
        conn = psycopg2.connect(
            dbname=settings.pg_db,
            user=settings.pg_user,
            password=settings.pg_password,
            host=settings.pg_host,
            port=settings.pg_port,
        )

        cur = conn.cursor()
        channel = 'schema_changes'

        # Execute the LISTEN query
        listen_query = f"LISTEN {channel};"
        cur.execute(listen_query)
        conn.commit()

        print(f"Listening for notifications on channel '{channel}'...")
        try:
            while True:
                # Wait for notifications
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    #
                    # On schema update/create, refresh the dynamic routes
                    # and clear the openapi cache -> new one will be regenerated
                    # during the next [GET /docs]
                    #
                    print(f"Received notification: {notify.payload}")
                    with SessionLocal() as db:
                        load_dynamic_routes(db=db, app=self.app_reference)
                    self.app_reference.openapi_schema = None
        finally:
            # Close cursor and connection
            cur.close()
            conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start the thread before the app startup -> can still be run as a single ASGI app.
    watcher_thread = Watcher(app)
    watcher_thread.start()
    yield


def create_app(session: Optional[Session] = None) -> FastAPI:
    app = FastAPI(description=generate_api_description(), lifespan=lifespan)
    origins = ['*']
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )

    if session:
        load_dynamic_routes(db=session, app=app)
    else:
        with SessionLocal() as db:
            load_dynamic_routes(db=db, app=app)

    app.include_router(router)
    return app
