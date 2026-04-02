"""LLM 클라이언트 팩토리.

LLM_PROVIDER 설정에 따라 Gemini 또는 OpenRouter 클라이언트를 생성한다.
두 프로바이더 모두 OpenAI 호환 API를 사용하므로 호출 코드는 동일하다.
"""

import logging

from openai import AsyncOpenAI

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm_client() -> AsyncOpenAI | None:
    """설정에 따라 적절한 LLM 클라이언트를 반환한다.

    Returns:
        AsyncOpenAI 클라이언트 또는 키 미설정 시 None.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY가 설정되지 않았습니다.")
            return None
        return AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=_GEMINI_BASE_URL,
        )

    # openrouter (기본 폴백)
    if not settings.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY가 설정되지 않았습니다.")
        return None
    return AsyncOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=_OPENROUTER_BASE_URL,
    )


def get_llm_model() -> str:
    """현재 프로바이더에 맞는 모델명을 반환한다."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        return settings.GEMINI_MODEL
    return settings.LLM_MODEL


def get_provider_name() -> str:
    """현재 프로바이더 표시명을 반환한다."""
    if settings.LLM_PROVIDER.lower() == "gemini":
        return f"Gemini ({settings.GEMINI_MODEL})"
    return f"OpenRouter ({settings.LLM_MODEL})"
