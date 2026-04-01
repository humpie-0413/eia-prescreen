"""Draft Copilot API 엔드포인트.

POST /api/screening/{id}/draft — 전체 초안 생성
POST /api/screening/{id}/draft/{section_id} — 특정 섹션만
GET  /api/draft/template — 평가서 템플릿 구조 조회
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.schemas.draft import (
    DraftFullResponse,
    DraftRequest,
    DraftSectionResponse,
    TemplateResponse,
)
from backend.app.services import screening_store
from backend.app.services.data_fetcher import DataFetcher
from backend.app.services.draft_copilot import DraftCopilot
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

router = APIRouter()
template_router = APIRouter()

_copilot = DraftCopilot()
_engine = RiskEngine()
_engine.load_rules()
_fetcher = DataFetcher()
_matcher = RegulationMatcher()


async def _get_screening_data(screening_id: str, body: DraftRequest) -> tuple[dict, list[dict], list[dict]]:
    """스크리닝 데이터에서 프로젝트 정보, 리스크 카드, 규제를 가져온다."""
    record = await screening_store.get(screening_id)

    # 프로젝트 정보 구성
    project_info: dict = {}
    if record:
        project_info = {
            "project_name": record.get("project_name", ""),
            "project_type": record.get("project_type", "other"),
            "project_scale": record.get("project_scale", ""),
            "address": record.get("address", ""),
        }

    # body 오버라이드
    if body.project_name:
        project_info["project_name"] = body.project_name
    if body.project_type:
        project_info["project_type"] = body.project_type
    if body.project_scale:
        project_info["project_scale"] = body.project_scale
    if body.address:
        project_info["address"] = body.address

    # 저장된 평가 결과 사용 또는 실시간 평가
    risk_cards: list[dict] = []
    regulations: list[dict] = []

    if record:
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


@router.post("/{screening_id}/draft", response_model=DraftFullResponse)
async def generate_full_draft(
    screening_id: str,
    body: DraftRequest,
) -> DraftFullResponse:
    """전체 초안을 생성한다."""
    project_info, risk_cards, regulations = await _get_screening_data(screening_id, body)

    result = await _copilot.generate_full_draft(
        project_info=project_info,
        risk_cards=risk_cards,
        regulations=regulations,
    )

    return DraftFullResponse(**result)


@router.post("/{screening_id}/draft/{section_id}", response_model=DraftSectionResponse)
async def generate_section_draft(
    screening_id: str,
    section_id: str,
    body: DraftRequest,
) -> DraftSectionResponse:
    """특정 섹션의 초안을 생성한다."""
    project_info, risk_cards, regulations = await _get_screening_data(screening_id, body)

    if body.use_llm:
        result = await _copilot.generate_with_llm(
            section_id=section_id,
            project_info=project_info,
            risk_cards=risk_cards,
            regulations=regulations,
        )
    else:
        result = await _copilot.generate_section(
            section_id=section_id,
            project_info=project_info,
            risk_cards=risk_cards,
            regulations=regulations,
        )

    if result is None:
        raise HTTPException(status_code=404, detail=f"섹션을 찾을 수 없습니다: {section_id}")

    return DraftSectionResponse(**result)


@template_router.get("/draft/template", response_model=TemplateResponse)
async def get_template() -> TemplateResponse:
    """평가서 템플릿 구조를 반환한다."""
    template = _copilot.get_template()
    return TemplateResponse(**template)
