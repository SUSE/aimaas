from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    pg_user: str
    pg_password: str
    pg_host: str
    pg_port: int = 5432
    pg_db: str
    
    test_pg_user: Optional[str]
    test_pg_password:  Optional[str]
    test_pg_host:  Optional[str]
    test_pg_port:  Optional[int] = 5432
    test_pg_db:  Optional[str]

    query_limit: Optional[int] = 10
    class Config:
        env_file = '.env'


settings = Settings()
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}@" \
                          f"{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
