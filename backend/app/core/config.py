from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # project root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eia_prescreen"
    POSTGRES_USER: str = "eia_user"
    POSTGRES_PASSWORD: str = "change_me_in_production"
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:  # noqa: ANN001
        if v:
            return v
        d = info.data
        return (
            f"postgresql+asyncpg://{d['POSTGRES_USER']}:{d['POSTGRES_PASSWORD']}"
            f"@{d['POSTGRES_HOST']}:{d['POSTGRES_PORT']}/{d['POSTGRES_DB']}"
        )

    # ── Backend ──
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    SECRET_KEY: str = "change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Frontend ──
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

    # ── LLM (OpenRouter) ──
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "deepseek/deepseek-chat"

    # ── 공공데이터 API ──
    DATA_GO_KR_API_KEY: str = ""
    VWORLD_API_KEY: str = ""
    AIRKOREA_API_KEY: str = ""
    EIASS_API_KEY: str = ""
    DATA_EX_API_KEY: str = ""  # 한국도로공사 실시간 교통량
    KHOA_API_KEY: str = ""  # 국립해양조사원
    WASTE_API_KEY: str = ""  # 폐기물 통계 (recycling-info.or.kr)
    WASTE_API_USERID: str = ""  # 폐기물 통계 사용자 ID

    # ── EIASS 로그인 ──
    EIASS_ID: str = ""
    EIASS_PW: str = ""

    # ── RAG ──
    RAG_EMBED_MODEL: str = "jhgan/ko-sroberta-multitask"

    # ── 캐시 ──
    CACHE_DIR: str = str(BASE_DIR / "data" / "snapshots")
    CACHE_TTL_HOURS: int = 24
    DEMO_MODE: bool = True
    ENVIRONMENT: str = "development"  # development / staging / production
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True


settings = Settings()
