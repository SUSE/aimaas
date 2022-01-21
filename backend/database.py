from fastapi import HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

db_exception = HTTPException(
    status_code=HTTP_503_SERVICE_UNAVAILABLE,
    detail='Database connection not possible'
)


class STATEMENTS:
    all_parent_groups = text("""
        with recursive ancestors(id, parent_id) as (
            select groups.id, groups.parent_id from groups where groups.id = any(:groupids)
            union all
            select groups.id, groups.parent_id from ancestors, groups where groups.id = ancestors.parent_id
        )

        select distinct id from ancestors;
        """)


def get_db():
    '''Database dependency for FastAPI'''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
