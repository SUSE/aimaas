from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings as s

SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{s.pg_user}:{s.pg_password}@{s.pg_host}:{s.pg_port}/{s.pg_db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    '''Database dependency for FastAPI'''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()