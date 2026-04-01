"""과거 환평 패턴 분석 API 엔드포인트."""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from backend.app.schemas.patterns import (
    OverallSummary,
    PatternResponse,
    PredictionResponse,
    SuggestedRulesResponse,
)
from backend.app.services.pattern_advisor import PatternAdvisor

logger = logging.getLogger(__name__)
router = APIRouter()

# 서비스 인스턴스
_advisor = PatternAdvisor()
_advisor.load()


# ──────────────────────────────────────────────────────────
# GET /api/patterns — 전체 분석 요약
# ──────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=OverallSummary,
    summary="전체 패턴 분석 요약",
    description="수집된 과거 환경영향평가 데이터의 전체 요약 통계를 반환한다.",
)
async def get_overall_summary() -> OverallSummary:
    data = _advisor.get_overall_summary()
    return OverallSummary(**data)


# ──────────────────────────────────────────────────────────
# GET /api/patterns/{project_type} — 사업유형별 패턴
# ──────────────────────────────────────────────────────────


@router.get(
    "/{project_type}",
    response_model=PatternResponse,
    summary="사업유형별 패턴 조회",
    description="사업유형별 과거 환평 패턴(협의결과, 빈출 지적항목, 통계)을 반환한다.",
)
async def get_patterns(project_type: str) -> PatternResponse:
    data = _advisor.get_patterns(project_type)

    # type_data를 스키마에 맞게 변환
    type_data_converted = []
    for td in data.get("type_data", []):
        common_issues = [
            {"issue": ci["issue"], "count": ci["count"], "pct": ci["pct"]}
            for ci in td.get("common_issues", [])
        ]
        type_data_converted.append({
            **td,
            "common_issues": common_issues,
        })

    return PatternResponse(
        project_type=data["project_type"],
        total_analyzed=data["total_analyzed"],
        overall_total=data["overall_total"],
        analysis_year_range=data.get("analysis_year_range", ""),
        type_data=type_data_converted,
    )


# ──────────────────────────────────────────────────────────
# GET /api/patterns/{project_type}/predict — 예상 지적항목 + 확률
# ──────────────────────────────────────────────────────────


@router.get(
    "/{project_type}/predict",
    response_model=PredictionResponse,
    summary="예상 지적항목 + 확률",
    description=(
        "과거 데이터 기반으로 해당 사업유형에서 예상되는 지적항목, "
        "협의결과 확률, 보완 패턴을 반환한다."
    ),
)
async def predict_issues(
    project_type: str,
    location_type: Optional[str] = Query(
        default=None,
        description="입지유형 (산지, 수변, 농지, 도시, 해안, 평지)",
    ),
) -> PredictionResponse:
    data = _advisor.predict_issues(project_type, location_type)
    return PredictionResponse(**data)


# ──────────────────────────────────────────────────────────
# GET /api/patterns/rules/suggested — 규칙 보강 제안
# ──────────────────────────────────────────────────────────


@router.get(
    "/rules/suggested",
    response_model=SuggestedRulesResponse,
    summary="규칙 보강 제안",
    description="과거 패턴 중 기존 64개 규칙에 없는 항목에 대한 신규 규칙 제안.",
)
async def get_suggested_rules() -> SuggestedRulesResponse:
    suggestions = _advisor.get_suggested_rules()
    return SuggestedRulesResponse(
        suggestions=suggestions,
        total=len(suggestions),
    )
