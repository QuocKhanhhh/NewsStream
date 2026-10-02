from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    elasticsearch_url: str = Field(default="http://elasticsearch:9200")
    elasticsearch_index: str = Field(default="newsstream.newsdb.news")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
