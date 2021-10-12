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
    test_pg_port:  Optional[int]
    test_pg_db:  Optional[str]

    class Config:
        env_file = '.env'

settings = Settings()
    