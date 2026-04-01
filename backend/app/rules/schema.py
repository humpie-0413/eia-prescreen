from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RuleCondition(BaseModel):
    """규칙 트리거 조건 정의."""

    field: str = Field(..., description="평가 대상 데이터 필드명")
    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte",
        "in", "not_in",
        "contains", "not_contains",
        "intersects", "within_buffer",
        "exists", "not_exists",
    ] = Field(..., description="비교 연산자")
    value: Any = Field(..., description="비교 기준값")
    unit: Optional[str] = Field(None, description="단위 (m, km, ppm 등)")


class RuleDefinition(BaseModel):
    """개별 규칙 정의."""

    rule_id: str = Field(..., pattern=r"^[A-Z]{2,4}-\d{3}$", description="규칙 ID (예: LAND-001)")
    rule_version: str = Field(default="v1", description="규칙 버전")
    title: str = Field(..., max_length=200, description="규칙 제목 (한글)")
    trigger_dataset: str = Field(..., description="트리거 데이터셋 (API/소스명)")
    condition: RuleCondition = Field(..., description="트리거 조건")
    severity: Literal["critical", "major", "review", "info"] = Field(
        ..., description="심각도",
    )
    rationale: str = Field(..., description="판정 근거 설명")
    evidence: str = Field(..., description="근거 데이터 출처/설명")
    next_action: str = Field(..., description="후속 조치 권고")
    legal_basis: Optional[str] = Field(None, description="관련 법령 조항")
    source_snapshot_date: Optional[date] = Field(
        None, description="데이터 기준일",
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="신뢰도 (0~1)",
    )
    human_review_required: bool = Field(
        default=False, description="전문가 검토 필요 여부",
    )


class RuleSet(BaseModel):
    """규칙 세트 — YAML 파일 하나에 대응."""

    version: str = Field(default="v1", description="규칙 세트 버전")
    domain: str = Field(..., description="규칙 영역 (land_regulation, ecology 등)")
    description: str = Field(..., description="규칙 세트 설명")
    rules: list[RuleDefinition] = Field(..., min_length=1, description="규칙 목록")
