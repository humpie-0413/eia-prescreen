import enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

logger = logging.getLogger(__name__)


class ConnectorStatus(str, enum.Enum):
    STABLE = "stable"
    UNSTABLE = "unstable"
    UNAVAILABLE = "unavailable"


class DataFreshness(BaseModel):
    """데이터 신선도 메타정보."""

    fetched_at: Optional[datetime] = Field(None, description="실시간 조회 시각")
    snapshot_at: Optional[datetime] = Field(None, description="스냅샷 저장 시각")
    fallback_used: bool = Field(default=False, description="캐시 폴백 사용 여부")
    freshness: str = Field(
        default="unknown",
        description="신선도 등급: live / cached / stale / unknown",
    )


class DataTier(str, enum.Enum):
    """데이터 전략 3계층."""

    A = "A"  # 안정형 실시간
    B = "B"  # 불안정형 + 캐시
    C = "C"  # 수동 스냅샷 / 큐레이션


class ConnectorResult(BaseModel):
    """커넥터 조회 결과."""

    connector_name: str
    tier: str
    status: ConnectorStatus
    freshness: DataFreshness
    data: Any = None
    error: Optional[str] = None


class BaseConnector(ABC):
    """커넥터 추상 기반 클래스.

    모든 외부 데이터 커넥터는 이 클래스를 상속해야 한다.
    """

    name: str = "base"
    tier: DataTier = DataTier.B
    description: str = ""

    @abstractmethod
    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        """실시간 API 호출로 데이터를 조회한다.

        Args:
            lng: 경도
            lat: 위도
            buffer_m: 버퍼 거리 (미터)

        Returns:
            ConnectorResult
        """
        ...

    def _make_empty_result(self, reason: str = "") -> ConnectorResult:
        """데이터를 확보하지 못했을 때 빈 결과를 반환한다 (에러가 아님)."""
        return ConnectorResult(
            connector_name=self.name,
            tier=self.tier.value,
            status=ConnectorStatus.UNAVAILABLE,
            freshness=DataFreshness(freshness="unavailable"),
            data=None,
            error=reason or "데이터 미확보",
        )

    async def fetch_with_retry(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        max_attempts: int = 3,
        **kwargs: Any,
    ) -> ConnectorResult:
        """fetch()를 exponential backoff로 재시도한다.

        1초 → 2초 → 4초 대기, 최대 3회 시도 후 실패 시 에러 반환.
        """
        attempt = 0
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                result = await self.fetch(lng, lat, buffer_m, **kwargs)
                if result.status != ConnectorStatus.UNAVAILABLE:
                    if attempt > 1:
                        logger.info(
                            "%s: succeeded on attempt %d/%d",
                            self.name, attempt, max_attempts,
                        )
                    return result
                last_error = result.error or "unavailable"
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "%s: attempt %d/%d failed: %s",
                    self.name, attempt, max_attempts, e,
                )

            if attempt < max_attempts:
                wait_seconds = 2 ** (attempt - 1)  # 1, 2, 4
                logger.info(
                    "%s: retrying in %ds (%d/%d)",
                    self.name, wait_seconds, attempt, max_attempts,
                )
                import asyncio
                await asyncio.sleep(wait_seconds)

        logger.error(
            "%s: all %d attempts failed: %s",
            self.name, max_attempts, last_error,
        )
        return self._make_error(f"All {max_attempts} attempts failed: {last_error}")

    def _make_result(
        self,
        data: Any,
        status: ConnectorStatus = ConnectorStatus.STABLE,
        freshness: Optional[DataFreshness] = None,
        error: Optional[str] = None,
    ) -> ConnectorResult:
        if freshness is None:
            freshness = DataFreshness(
                fetched_at=datetime.now(),
                freshness="live",
            )
        return ConnectorResult(
            connector_name=self.name,
            tier=self.tier.value,
            status=status,
            freshness=freshness,
            data=data,
            error=error,
        )

    def _make_error(self, error: str) -> ConnectorResult:
        return ConnectorResult(
            connector_name=self.name,
            tier=self.tier.value,
            status=ConnectorStatus.UNAVAILABLE,
            freshness=DataFreshness(freshness="unknown"),
            data=None,
            error=error,
        )
