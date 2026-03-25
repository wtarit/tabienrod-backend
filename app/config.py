from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pg_conn_string: str
    mailgun_api_key: str
    mailgun_domain: str
    base_url: str = "http://localhost:8000"
    s3_bucket_name: str | None = None
    s3_endpoint_url: str | None = None
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None


settings = Settings()
