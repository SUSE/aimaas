from datetime import timedelta, timezone
from typing import Optional, Union, List

from fastapi_pagination import Params
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
    use_ssl: bool = False
    bind_template: str = "uid={username},cn=users,dc=suse,dc=de"
    search_template: str = "(uid={username})"
    attr: LdapAttributeMap = LdapAttributeMap()
    timeout: int = 5

    class Config:
        env_file = '.env'
        env_prefix = 'LDAP_'


class HelpSettings(BaseSettings):
    source_url: str = "https://github.com/SUSE/aimaas"
    chat_url: Optional[str] = None
    tracker_url: str = "https://github.com/SUSE/aimaas/issues"
    email: Optional[str] = None

    class Config:
        env_file = '.env'
        env_prefix = 'HELP_'


class Settings(BaseSettings):
    pg_user: str
    pg_password: str
    pg_host: str
    pg_port: int = 5432
    pg_db: str
    pg_client_encoding: str = "utf8"

    default_page_size: int = 10
    timezone_offset: Union[str, int] = "utc"

    auth_backends: str = "local"
    secret: str = "this is an insecure dummy. replace it in production!"
    token_url = "/login"
    pwd_hash_alg: str = 'HS256'  # list of options can be found in jose.jwt.ALGORITHMS
    token_exp_minutes: int = 120

    ldap: LdapSettings = LdapSettings()
    help: HelpSettings = HelpSettings()

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
DEFAULT_PARAMS = Params(page=1, size=settings.default_page_size)
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}@" \
                          f"{settings.pg_host}:{settings.pg_port}/{settings.pg_db}?"\
                          f"client_encoding={settings.pg_client_encoding}"
VERSION = "0.3.3"
