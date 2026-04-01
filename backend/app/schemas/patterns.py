"""패턴 분석 API 응답 스키마."""

from pydantic import BaseModel, Field


class IssueItem(BaseModel):
    """개별 지적항목."""
    issue: str
    count: int = 0
    pct: float = 0.0


class TypePatternDetail(BaseModel):
    """한국어 사업유형별 상세 패턴."""
    korean_type: str
    total_count: int
    consultation_results: dict[str, int] = {}
    result_pct: dict[str, float] = {}
    common_issues: list[IssueItem] = []
    avg_review_months: float | None = None
    supplement_required_pct: float | None = None


class PatternResponse(BaseModel):
    """GET /api/patterns/{project_type} 응답."""
    project_type: str
    total_analyzed: int
    overall_total: int
    analysis_year_range: str = ""
    type_data: list[TypePatternDetail] = []


class PredictedIssue(BaseModel):
    """예상 지적항목."""
    issue: str
    probability_pct: float
    past_count: int
    total_in_type: int
    description: str


class RiskAssessment(BaseModel):
    """입지 리스크 평가."""
    location_type: str
    risk_level: str
    issue_probability: float
    top_issues: list[str] = []
    supplement_probability_pct: float


class RemediationSuggestion(BaseModel):
    """보완 패턴 제안."""
    issue: str
    common_remediation: list[str] = []
    frequency: float


class PredictionResponse(BaseModel):
    """GET /api/patterns/{project_type}/predict 응답."""
    project_type: str
    korean_type: str
    total_in_type: int
    predicted_issues: list[PredictedIssue] = []
    consultation_prediction: dict[str, float] = {}
    avg_review_months: float | None = None
    supplement_required_pct: float | None = None
    risk_assessment: RiskAssessment | None = None
    remediation_suggestions: list[RemediationSuggestion] = []


class SuggestedRule(BaseModel):
    """규칙 보강 제안."""
    suggestion_id: str
    title: str
    source_type: str
    issue: str
    evidence: str
    recommended_severity: str
    rationale: str


class SuggestedRulesResponse(BaseModel):
    """규칙 보강 제안 목록."""
    suggestions: list[SuggestedRule] = []
    total: int = 0


class OverallSummary(BaseModel):
    """전체 분석 데이터 요약."""
    total_count: int
    year_range: str = ""
    analyzed_at: str = ""
    unique_biz_types: int = 0
    biz_type_distribution: dict[str, int] = {}
    step_distribution: dict[str, int] = {}
    available_types: list[str] = []
