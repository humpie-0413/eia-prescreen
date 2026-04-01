"""데이터 가용성 API 응답 스키마."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConnectorFreshnessResponse(BaseModel):
    """데이터 신선도 정보."""

    fetched_at: Optional[datetime] = Field(None, description="실시간 조회 시각")
    snapshot_at: Optional[datetime] = Field(None, description="스냅샷 저장 시각")
    fallback_used: bool = Field(default=False, description="캐시 폴백 사용 여부")
    freshness: str = Field(
        default="unknown",
        description="신선도 등급: live / cached / stale / demo / unknown",
    )


class ConnectorStatusResponse(BaseModel):
    """커넥터 상태 정보."""

    name: str = Field(..., description="커넥터 이름 (e.g. land_use)")
    tier: str = Field(..., description="데이터 계층 (A/B/C)")
    description: str = Field(..., description="커넥터 설명")
    status: str = Field(
        ..., description="상태: stable / unstable / unavailable / unknown"
    )
    freshness: Optional[ConnectorFreshnessResponse] = Field(
        None, description="신선도 정보"
    )
    has_data: bool = Field(default=False, description="데이터 존재 여부")
    error: Optional[str] = Field(None, description="에러 메시지")
    last_success_at: Optional[datetime] = Field(
        None, description="마지막 성공 조회 시각"
    )


class ScreeningDataStatusResponse(BaseModel):
    """스크리닝별 데이터 가용성 응답."""

    screening_id: Optional[str] = Field(None, description="스크리닝 ID")
    connectors: list[ConnectorStatusResponse] = Field(
        default_factory=list, description="커넥터별 상태 목록"
    )
    total: int = Field(..., description="전체 커넥터 수")
    available: int = Field(..., description="데이터가 있는 커넥터 수")
    coverage_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description="전체 데이터 커버리지 퍼센트 (0~100)",
    )
    freshness_summary: dict[str, int] = Field(
        default_factory=dict,
        description="신선도 레벨별 커넥터 수 (live/cached/stale/unknown)",
    )


class ConnectorListResponse(BaseModel):
    """전체 커넥터 목록 응답."""

    connectors: list[ConnectorStatusResponse] = Field(
        default_factory=list, description="등록된 커넥터 목록"
    )
    total: int = Field(..., description="전체 커넥터 수")
