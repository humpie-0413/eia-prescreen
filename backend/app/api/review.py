"""검토의견 예측 + 품질 체크 API 엔드포인트.

POST /api/screening/{id}/predict-review — 예상 검토의견
POST /api/screening/{id}/quality-check — 품질 체크
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.app.schemas.review import (
    QualityCheckRequest,
    QualityCheckResponse,
    ReviewPredictionRequest,
    ReviewPredictionResponse,
)
from backend.app.services import screening_store
from backend.app.services.data_fetcher import DataFetcher
from backend.app.services.draft_copilot import DraftCopilot
from backend.app.services.quality_checker import QualityChecker
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.review_predictor import ReviewPredictor
from backend.app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

router = APIRouter()

_predictor = ReviewPredictor()
_checker = QualityChecker()
_copilot = DraftCopilot()
_engine = RiskEngine()
_engine.load_rules()
_fetcher = DataFetcher()
_matcher = RegulationMatcher()


async def _get_screening_eval(screening_id: str) -> tuple[dict, list[dict], list[dict]]:
    """스크리닝에서 프로젝트 정보, 리스크 카드, 규제를 가져온다."""
    record = await screening_store.get(screening_id)

    project_info: dict = {"project_type": "other"}
    risk_cards: list[dict] = []
    regulations: list[dict] = []

    if record:
        project_info = {
            "project_name": record.get("project_name", ""),
            "project_type": record.get("project_type", "other"),
            "project_scale": record.get("project_scale", ""),
            "address": record.get("address", ""),
        }

        stored_risks = record.get("risk_cards", [])
        if stored_risks:
            risk_cards = [r if isinstance(r, dict) else r.model_dump() if hasattr(r, "model_dump") else {} for r in stored_risks]
            stored_regs = record.get("regulation_matches", [])
            regulations = [r if isinstance(r, dict) else {} for r in stored_regs]
        else:
            lng = record.get("lng")
            lat = record.get("lat")
            if lng is not None and lat is not None:
                spatial = await _fetcher.fetch_all_as_spatial_data(lng, lat)
                risk_results = _engine.evaluate(project_info, spatial)
                reg_results = _matcher.match(project_info, spatial)
                risk_cards = [r.model_dump() for r in risk_results]
                regulations = [
                    {"regulation_name": r.regulation_name, "legal_basis": r.legal_basis,
                     "permit_required": r.permit_required, "related_authority": r.related_authority}
                    for r in reg_results
                ]

    return project_info, risk_cards, regulations


@router.post("/{screening_id}/predict-review", response_model=ReviewPredictionResponse)
async def predict_review(
    screening_id: str,
    body: ReviewPredictionRequest,
) -> ReviewPredictionResponse:
    """예상 검토의견을 생성한다."""
    project_info, risk_cards, _ = await _get_screening_eval(screening_id)

    result = _predictor.predict_review_comments(
        project_type=project_info["project_type"],
        risk_cards=risk_cards,
    )

    return ReviewPredictionResponse(**result)


@router.post("/{screening_id}/quality-check", response_model=QualityCheckResponse)
async def quality_check(
    screening_id: str,
    body: QualityCheckRequest,
) -> QualityCheckResponse:
    """품질 체크를 수행한다."""
    project_info, risk_cards, regulations = await _get_screening_eval(screening_id)

    # 초안 생성 (품질 체크 대상)
    draft = await _copilot.generate_full_draft(
        project_info=project_info,
        risk_cards=risk_cards,
        regulations=regulations,
    )

    result = _checker.check(
        project_type=project_info["project_type"],
        risk_cards=risk_cards,
        regulations=regulations,
        draft_sections=draft["sections"],
    )

    return QualityCheckResponse(**result)
