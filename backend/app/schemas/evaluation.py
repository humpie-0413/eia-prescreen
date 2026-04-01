from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """리스크 평가 요청."""
    force: bool = Field(False, description="True면 캐시 무시하고 재평가")


class RiskCardEvalResult(BaseModel):
    """리스크 카드 평가 결과 (DB 저장 전)."""
    rule_id: str
    rule_version: str
    title: str
    severity: str  # critical/major/review/info
    rationale: str
    evidence: dict | None = None
    next_action: str | None = None
    legal_basis: str | None = None
    confidence: float | None = None
    human_review_required: bool = False
    trigger_dataset: str | None = None
    source_snapshot_date: datetime | None = None


class RegulationMatchEvalResult(BaseModel):
    """규제 매칭 결과."""
    regulation_name: str
    regulation_code: str | None = None
    legal_basis: str
    description: str | None = None
    restriction_level: str | None = None
    permit_required: bool = False
    related_authority: str | None = None
    evidence: dict | None = None


class EvaluationSummary(BaseModel):
    """평가 요약."""
    total_risks: int = 0
    critical_count: int = 0
    major_count: int = 0
    review_count: int = 0
    info_count: int = 0
    total_regulations: int = 0
    permit_required_count: int = 0


class EvaluationResponse(BaseModel):
    """리스크 평가 + 규제 매칭 통합 응답."""
    screening_id: str
    status: str  # "evaluated"
    risk_cards: list[RiskCardEvalResult] = []
    regulation_matches: list[RegulationMatchEvalResult] = []
    summary: EvaluationSummary


class ChecklistItemResponse(BaseModel):
    id: int
    category: str
    title: str
    description: str
    legal_basis: str | None = None
    priority: str  # 필수/권고/참고
    checked: bool = False
    related_rule_id: str | None = None


class ChecklistSectionResponse(BaseModel):
    section_name: str
    priority: str
    items: list[ChecklistItemResponse] = []


class ChecklistResponse(BaseModel):
    screening_id: str | None = None
    total_items: int = 0
    sections: list[ChecklistSectionResponse] = []
    generated_at: str
