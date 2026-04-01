import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── 입력 스키마 ──


class LocationInput(BaseModel):
    """위치 좌표 (경도, 위도)."""

    lng: float = Field(..., ge=-180, le=180, description="경도")
    lat: float = Field(..., ge=-90, le=90, description="위도")


class ScreeningInput(BaseModel):
    """스크리닝 요청 입력."""

    project_name: str = Field(..., min_length=1, max_length=200)
    project_type: str = Field(
        ...,
        pattern="^(urban_dev|industrial|energy|port|road|water_resource|railway|airport|river|tourism|mountain|sports|waste|military|mining|reclamation|special_area|etc|housing|power_plant|factory|other)$",
        description="사업유형",
    )
    project_scale: Optional[str] = Field(None, max_length=100, description="사업규모")
    address: Optional[str] = Field(None, max_length=500, description="주소")
    location: Optional[LocationInput] = None
    boundary_geojson: Optional[dict] = Field(
        None,
        description="사업 경계 GeoJSON (Polygon)",
    )


# ── 출력 스키마 ──


class RiskCardResponse(BaseModel):
    """리스크 카드 응답."""

    model_config = {"from_attributes": True}

    id: UUID = Field(default_factory=uuid.uuid4)
    rule_id: str
    rule_version: str
    title: str
    severity: str
    rationale: str
    evidence: Optional[dict] = None
    next_action: Optional[str] = None
    legal_basis: Optional[str] = None
    confidence: Optional[float] = None
    human_review_required: bool
    trigger_dataset: Optional[str] = None
    source_snapshot_date: Optional[datetime] = None


class RegulationMatchResponse(BaseModel):
    """규제 매칭 응답."""

    model_config = {"from_attributes": True}

    id: UUID = Field(default_factory=uuid.uuid4)
    regulation_name: str
    regulation_code: Optional[str] = None
    legal_basis: Optional[str] = None
    description: Optional[str] = None
    restriction_level: Optional[str] = None
    permit_required: bool
    related_authority: Optional[str] = None
    evidence: Optional[dict] = None


class ScreeningResponse(BaseModel):
    """스크리닝 결과 전체 응답."""

    model_config = {"from_attributes": True}

    id: UUID
    project_name: str
    project_type: str
    project_scale: Optional[str] = None
    address: Optional[str] = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    status: str
    llm_interpretation: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    risk_cards: list[RiskCardResponse] = []
    regulation_matches: list[RegulationMatchResponse] = []


class ScreeningSummary(BaseModel):
    """스크리닝 목록용 요약 응답."""

    model_config = {"from_attributes": True}

    id: UUID
    project_name: str
    project_type: str
    status: str
    created_at: datetime
    risk_card_count: int = 0
    critical_count: int = 0
    major_count: int = 0
