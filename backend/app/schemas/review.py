"""검토의견 예측 + 품질 체크 Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── 검토의견 예측 ──


class PredictedComment(BaseModel):
    """예상 검토의견."""

    category: str
    comment: str
    probability_pct: float
    past_count: int
    total_past_cases: int
    risk_matched: bool = False
    severity: str = "medium"


class ReviewPredictionResponse(BaseModel):
    """검토의견 예측 응답."""

    project_type: str
    korean_type: str
    total_past_cases: int
    predicted_comments: list[PredictedComment] = Field(default_factory=list)
    avg_review_months: float | None = None
    supplement_required_pct: float | None = None
    disclaimer: str = "이 예측은 과거 통계 기반 참고 자료이며, 실제 검토의견과 다를 수 있습니다"


class ReviewPredictionRequest(BaseModel):
    """검토의견 예측 요청."""
    pass


# ��─ 품질 체크 ──


class QualityCheckItem(BaseModel):
    """개별 품질 체크 항목."""

    check_id: str
    category: str
    title: str
    status: str  # "pass" | "warning" | "fail"
    detail: str


class QualityCheckResponse(BaseModel):
    """품질 체크 응답."""

    overall_status: str  # "pass" | "warning" | "fail"
    score: int
    total_checks: int
    passed: int
    warnings: int
    failed: int
    checks: list[QualityCheckItem] = Field(default_factory=list)
    summary: dict[str, str] = Field(default_factory=dict)


class QualityCheckRequest(BaseModel):
    """품질 체크 요청."""
    pass
