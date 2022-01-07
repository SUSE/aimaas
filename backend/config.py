from datetime import timedelta, timezone
from typing import Optional, Union

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

    timezone_offset: Union[str, int] = "utc"
    secret: str = "this is an insecure dummy. replace it in production!"

    pwd_hash_alg: str = 'HS256'  # list of options can be found in jose.jwt.ALGORITHMS
    token_exp_minutes: int = 120


    class Config:
        env_file = '.env'

    @property
    def timezone(self) -> timezone:
        if self.timezone_offset == "utc":
            return timezone.utc
        if not isinstance(self.timezone_offset, int):
            raise ValueError("Only 'utc' is an acceptable string representation for timezones")

        return timezone(timedelta(hours=self.timezone_offset))


settings = Settings()
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}@" \
                          f"{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
