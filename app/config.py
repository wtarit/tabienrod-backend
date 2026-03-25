from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pg_conn_string: str
    mailgun_api_key: str
    mailgun_domain: str
    base_url: str = "http://localhost:8000"


settings = Settings()
