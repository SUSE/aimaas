from datetime import timedelta, timezone
from typing import Optional, Union, List

from pydantic import BaseSettings


class LdapAttributeMap(BaseSettings):
    username: str = "uid"
    email: str = "mail"
    firstname: str = "givenName"
    lastname: str = "sn"

    class Config:
        env_file = '.env'
        env_prefix = 'LDAP_ATTR_'


class LdapSettings(BaseSettings):
    user: str = "uid=username,cn=users,dc=suse,dc=de"
    password: str = "secret"
    host: str = "example.com"
    bind_template: str = "uid={username},cn=users,dc=suse,dc=de"
    search_template: str = "(uid={username})"
    attr: LdapAttributeMap = LdapAttributeMap()
    timeout: int = 5

    class Config:
        env_file = '.env'
        env_prefix = 'LDAP_'


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

    auth_backends: str = "local"
    secret: str = "this is an insecure dummy. replace it in production!"
    token_url = "/login"
    pwd_hash_alg: str = 'HS256'  # list of options can be found in jose.jwt.ALGORITHMS
    token_exp_minutes: int = 120

    ldap: LdapSettings = LdapSettings()

    class Config:
        env_file = '.env'

    @property
    def timezone(self) -> timezone:
        if self.timezone_offset == "utc":
            return timezone.utc
        if not isinstance(self.timezone_offset, int):
            raise ValueError("Only 'utc' is an acceptable string representation for timezones")

        return timezone(timedelta(hours=self.timezone_offset))

    @property
    def backends(self) -> List[str]:
        return self.auth_backends.split(",")


settings = Settings()
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}@" \
                          f"{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
