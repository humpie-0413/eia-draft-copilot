from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EIA Draft Copilot API"
    DEBUG: bool = False

    # PostgreSQL + PostGIS
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot"

    # CORS 허용 오리진 (쉼표 구분)
    CORS_ORIGINS: str = "http://localhost:3000"

    # 공공데이터포털 API 키 (에어코리아 대기질, 물환경정보시스템 등)
    DATA_GO_KR_API_KEY: str = ""

    # OpenAI API 키
    OPENAI_API_KEY: str = ""

    # Google API 키
    GOOGLE_API_KEY: str = ""

    # V-world API 키 (토지이용계획 조회)
    VWORLD_API_KEY: str = ""

    # LLM adapter 설정 (none | openai_paid | gemini_free)
    LLM_ADAPTER: str = "none"

    # API 호출 타임아웃 (초)
    CONNECTOR_TIMEOUT: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS를 리스트로 변환"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Sync URL for Alembic (asyncpg → psycopg2)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
