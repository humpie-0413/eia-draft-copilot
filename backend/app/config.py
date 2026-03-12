from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EIA Draft Copilot API"
    DEBUG: bool = False

    # PostgreSQL + PostGIS
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot"

    # 공공데이터포털 API 키 (에어코리아 대기질, 물환경정보시스템 등)
    DATA_GO_KR_API_KEY: str = ""

    # OpenAI API 키
    OPENAI_API_KEY: str = ""

    # Google API 키
    GOOGLE_API_KEY: str = ""

    # API 호출 타임아웃 (초)
    CONNECTOR_TIMEOUT: int = 30

    # Sync URL for Alembic (asyncpg → psycopg2)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
