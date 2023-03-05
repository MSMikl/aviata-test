from pydantic import BaseSettings


class Env(BaseSettings):
    MONGO_DB_URL: str
    PROVIDERS_URLS: list[str] = list()
    CURRENCY_RATES_URL: str = ''

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True
        env_nested_delimiter = '__'


ENV = Env()
