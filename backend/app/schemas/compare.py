"""부지 비교 스키마."""

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    """부지 비교 요청."""
    screening_ids: list[str] = Field(
        ..., min_length=2, max_length=3,
        description="비교할 스크리닝 ID 목록 (2~3개)"
    )


class SiteRiskSummary(BaseModel):
    """부지별 리스크 요약."""
    screening_id: str
    project_name: str
    project_type: str
    address: str | None = None
    total_risks: int = 0
    critical_count: int = 0
    major_count: int = 0
    review_count: int = 0
    info_count: int = 0
    total_regulations: int = 0
    permit_required_count: int = 0
    risk_cards: list[dict] = []
    regulation_matches: list[dict] = []


class RiskComparisonRow(BaseModel):
    """리스크 비교 행 (하나의 리스크 항목)."""
    rule_id: str
    title: str
    severity_by_site: dict[str, str | None] = {}  # screening_id -> severity or None


class CompareResponse(BaseModel):
    """부지 비교 응답."""
    sites: list[SiteRiskSummary]
    risk_matrix: list[RiskComparisonRow]
    recommendation: str  # 종합 추천 텍스트
