from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "local"
    LOG_LEVEL: str = "DEBUG"


settings = Settings()
