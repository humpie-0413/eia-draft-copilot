from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EIA Draft Copilot API"
    DEBUG: bool = False

    # PostgreSQL + PostGIS
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot"

    # Sync URL for Alembic (asyncpg → psycopg2)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
