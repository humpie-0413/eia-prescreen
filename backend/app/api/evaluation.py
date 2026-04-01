"""리스크 평가 · 규제 매칭 · 체크리스트 API 엔드포인트."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.database import check_db_connection, get_session
from backend.app.models.screening import (
    RegulationMatch,
    RiskCard,
    ScreeningRequest,
    Severity,
)
from backend.app.schemas.evaluation import (
    ChecklistResponse as ChecklistSchemaResponse,
    ChecklistItemResponse,
    ChecklistSectionResponse,
    EvaluateRequest,
    EvaluationResponse,
    EvaluationSummary,
    RegulationMatchEvalResult,
    RiskCardEvalResult,
)
from backend.app.schemas.screening import RegulationMatchResponse
from backend.app.services import screening_store
from backend.app.services.checklist_generator import ChecklistGenerator
from backend.app.services.data_fetcher import DataFetcher
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# ── 서비스 인스턴스 ──

_engine = RiskEngine()
_engine.load_rules()

_fetcher = DataFetcher()
_matcher = RegulationMatcher()
_checklist_gen = ChecklistGenerator()


def _get_project_info(record: dict) -> dict:
    """screening_store 레코드에서 프로젝트 정보를 추출한다."""
    return {
        "project_type": record.get("project_type", "other"),
        "project_name": record.get("project_name", ""),
        "project_scale": record.get("project_scale", ""),
        "address": record.get("address", ""),
    }


# ──────────────────────────────────────────────────────────
# POST /api/screening/{id}/evaluate — 리스크 분석 실행
# ──────────────────────────────────────────────────────────


@router.post(
    "/{screening_id}/evaluate",
    response_model=EvaluationResponse,
    summary="리스크 분석 실행",
    description="스크리닝 대상 부지에 대해 리스크 엔진 + 규제 매칭을 실행하고 결과를 반환한다.",
)
async def evaluate_screening(
    screening_id: str,
    body: EvaluateRequest,
) -> EvaluationResponse:
    # 스크리닝 데이터 조회
    record = await screening_store.get(screening_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Screening not found")

    # 이미 평가 완료된 경우 캐시 결과 반환 (재호출 방지)
    if (
        not body.force
        and record.get("status") == "evaluated"
        and record.get("risk_cards") is not None
    ):
        cached_risks = record.get("risk_cards", [])
        cached_regs = record.get("regulation_matches", [])
        risk_card_responses = [
            RiskCardEvalResult(**r) if isinstance(r, dict) else r
            for r in cached_risks
        ]
        reg_responses = [
            RegulationMatchEvalResult(**r) if isinstance(r, dict) else r
            for r in cached_regs
        ]
        summary = EvaluationSummary(
            total_risks=len(risk_card_responses),
            critical_count=sum(1 for r in cached_risks if (r.get("severity") if isinstance(r, dict) else r.severity) == "critical"),
            major_count=sum(1 for r in cached_risks if (r.get("severity") if isinstance(r, dict) else r.severity) == "major"),
            review_count=sum(1 for r in cached_risks if (r.get("severity") if isinstance(r, dict) else r.severity) == "review"),
            info_count=sum(1 for r in cached_risks if (r.get("severity") if isinstance(r, dict) else r.severity) == "info"),
            total_regulations=len(reg_responses),
            permit_required_count=sum(1 for r in cached_regs if (r.get("permit_required") if isinstance(r, dict) else r.permit_required)),
        )
        logger.info("Returning cached evaluation for %s", screening_id)
        return EvaluationResponse(
            screening_id=str(screening_id),
            status="evaluated",
            risk_cards=risk_card_responses,
            regulation_matches=reg_responses,
            summary=summary,
        )

    lng = record.get("lng")
    lat = record.get("lat")
    if lng is None or lat is None:
        raise HTTPException(status_code=400, detail="스크리닝에 좌표가 설정되지 않았습니다")

    # 프로젝트 정보
    project_info = _get_project_info(record)

    # 데이터 수집 (project_type 전달 → 룰 필드 정규화에 사용)
    spatial_data = await _fetcher.fetch_all_as_spatial_data(
        lng, lat, project_type=project_info.get("project_type"),
    )

    # 리스크 엔진 평가
    risk_results = _engine.evaluate(project_info, spatial_data)

    # 규제 매칭
    reg_results = _matcher.match(project_info, spatial_data)

    # 인메모리 저장
    risk_dicts = [r.model_dump() for r in risk_results]
    reg_dicts = [
        {
            "regulation_name": reg.regulation_name,
            "regulation_code": reg.regulation_code,
            "legal_basis": reg.legal_basis,
            "description": reg.description,
            "restriction_level": reg.restriction_level,
            "permit_required": reg.permit_required,
            "related_authority": reg.related_authority,
            "evidence": reg.evidence,
        }
        for reg in reg_results
    ]
    await screening_store.update_evaluation(screening_id, risk_dicts, reg_dicts)

    # DB 저장 (가능한 경우만)
    db_ok = await check_db_connection()
    if db_ok:
        try:
            session_gen = get_session()
            session = await session_gen.__anext__()
            try:
                stmt = select(ScreeningRequest).where(ScreeningRequest.id == UUID(screening_id))
                result = await session.execute(stmt)
                screening = result.scalar_one_or_none()
                if screening:
                    for old_card in screening.risk_cards:
                        await session.delete(old_card)
                    for old_reg in screening.regulation_matches:
                        await session.delete(old_reg)
                    for r in risk_results:
                        session.add(RiskCard(
                            screening_request_id=screening.id,
                            rule_id=r.rule_id, rule_version=r.rule_version,
                            title=r.title, severity=Severity(r.severity),
                            rationale=r.rationale, evidence=r.evidence,
                            next_action=r.next_action, legal_basis=r.legal_basis,
                            confidence=r.confidence, human_review_required=r.human_review_required,
                            trigger_dataset=r.trigger_dataset, source_snapshot_date=r.source_snapshot_date,
                        ))
                    for reg in reg_results:
                        session.add(RegulationMatch(
                            screening_request_id=screening.id,
                            regulation_name=reg.regulation_name, regulation_code=reg.regulation_code,
                            legal_basis=reg.legal_basis, description=reg.description,
                            restriction_level=reg.restriction_level, permit_required=reg.permit_required,
                            related_authority=reg.related_authority, evidence=reg.evidence,
                        ))
                    screening.status = "evaluated"
                    await session.commit()
            finally:
                await session_gen.aclose()
        except Exception:
            logger.warning("DB save failed — evaluation results kept in memory only")

    # 응답 생성
    risk_card_responses = [
        RiskCardEvalResult(
            rule_id=r.rule_id, rule_version=r.rule_version,
            title=r.title, severity=r.severity,
            rationale=r.rationale, evidence=r.evidence,
            next_action=r.next_action, legal_basis=r.legal_basis,
            confidence=r.confidence, human_review_required=r.human_review_required,
            trigger_dataset=r.trigger_dataset, source_snapshot_date=r.source_snapshot_date,
        )
        for r in risk_results
    ]

    reg_responses = [
        RegulationMatchEvalResult(
            regulation_name=reg.regulation_name, regulation_code=reg.regulation_code,
            legal_basis=reg.legal_basis, description=reg.description,
            restriction_level=reg.restriction_level, permit_required=reg.permit_required,
            related_authority=reg.related_authority, evidence=reg.evidence,
        )
        for reg in reg_results
    ]

    summary = EvaluationSummary(
        total_risks=len(risk_results),
        critical_count=sum(1 for r in risk_results if r.severity == "critical"),
        major_count=sum(1 for r in risk_results if r.severity == "major"),
        review_count=sum(1 for r in risk_results if r.severity == "review"),
        info_count=sum(1 for r in risk_results if r.severity == "info"),
        total_regulations=len(reg_results),
        permit_required_count=sum(1 for r in reg_results if r.permit_required),
    )

    return EvaluationResponse(
        screening_id=str(screening_id),
        status="evaluated",
        risk_cards=risk_card_responses,
        regulation_matches=reg_responses,
        summary=summary,
    )


# ──────────────────────────────────────────────────────────
# GET /api/screening/{id}/regulations — 규제 매칭 결과
# ──────────────────────────────────────────────────────────


@router.get(
    "/{screening_id}/regulations",
    response_model=list[RegulationMatchResponse],
    summary="규제 매칭 결과 조회",
    description="저장된 규제 매칭 결과를 반환한다. 먼저 evaluate를 실행해야 한다.",
)
async def get_regulations(
    screening_id: UUID,
) -> list[RegulationMatchResponse]:
    sid = str(screening_id)

    # 1) 인메모리 저장소에서 먼저 조회 (DB 없이도 동작)
    record = await screening_store.get(sid)
    if record:
        stored_regs = record.get("regulation_matches", [])
        if stored_regs:
            return [
                RegulationMatchResponse(**r) if isinstance(r, dict) else r
                for r in stored_regs
            ]

    # 2) DB에서 조회 (인메모리에 없을 때)
    db_ok = await check_db_connection()
    if not db_ok:
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening {screening_id} not found",
            )
        return []

    session_gen = get_session()
    session: AsyncSession = await session_gen.__anext__()
    try:
        stmt = (
            select(ScreeningRequest)
            .where(ScreeningRequest.id == screening_id)
            .options(selectinload(ScreeningRequest.regulation_matches))
        )
        result = await session.execute(stmt)
        screening = result.scalar_one_or_none()

        if screening is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening {screening_id} not found",
            )

        return screening.regulation_matches
    finally:
        await session_gen.aclose()


# ──────────────────────────────────────────────────────────
# GET /api/screening/{id}/checklist — 현장조사 체크리스트
# ──────────────────────────────────────────────────────────


@router.get(
    "/{screening_id}/checklist",
    response_model=ChecklistSchemaResponse,
    summary="현장조사 체크리스트",
    description="저장된 리스크 카드 + 규제를 기반으로 현장조사 체크리스트를 생성한다.",
)
async def get_checklist(
    screening_id: UUID,
) -> ChecklistSchemaResponse:
    sid = str(screening_id)
    record = await screening_store.get(sid)

    risk_dicts: list[dict] = []
    reg_dicts: list[dict] = []

    if record:
        stored_risks = record.get("risk_cards", [])
        stored_regs = record.get("regulation_matches", [])

        # 저장된 평가 결과가 있으면 사용
        if stored_risks:
            for r in stored_risks:
                if isinstance(r, dict):
                    risk_dicts.append(r)
                else:
                    risk_dicts.append({
                        "rule_id": r.rule_id, "title": r.title,
                        "severity": r.severity.value if hasattr(r.severity, "value") else r.severity,
                        "next_action": r.next_action, "legal_basis": r.legal_basis,
                    })
            for r in stored_regs:
                if isinstance(r, dict):
                    reg_dicts.append(r)
                else:
                    reg_dicts.append({
                        "regulation_name": r.regulation_name,
                        "regulation_code": r.regulation_code,
                        "legal_basis": r.legal_basis,
                        "description": r.description,
                        "permit_required": r.permit_required,
                        "related_authority": r.related_authority,
                    })
        else:
            # 저장된 결과가 없으면 실시간 평가
            lng = record.get("lng")
            lat = record.get("lat")
            if lng is not None and lat is not None:
                project_info = _get_project_info(record)
                spatial_data = await _fetcher.fetch_all_as_spatial_data(
                    lng, lat, project_type=project_info.get("project_type"),
                )
                risk_results = _engine.evaluate(project_info, spatial_data)
                reg_results = _matcher.match(project_info, spatial_data)
                risk_dicts = [
                    {"rule_id": r.rule_id, "title": r.title, "severity": r.severity,
                     "next_action": r.next_action, "legal_basis": r.legal_basis}
                    for r in risk_results
                ]
                reg_dicts = [
                    {"regulation_name": r.regulation_name, "regulation_code": r.regulation_code,
                     "legal_basis": r.legal_basis, "description": r.description,
                     "permit_required": r.permit_required, "related_authority": r.related_authority}
                    for r in reg_results
                ]

    checklist = _checklist_gen.generate(
        risk_dicts, reg_dicts, screening_id=sid
    )

    sections = [
        ChecklistSectionResponse(
            section_name=s.section_name,
            priority=s.priority,
            items=[
                ChecklistItemResponse(
                    id=item.id,
                    category=item.category,
                    title=item.title,
                    description=item.description,
                    legal_basis=item.legal_basis,
                    priority=item.priority,
                    checked=item.checked,
                    related_rule_id=item.related_rule_id,
                )
                for item in s.items
            ],
        )
        for s in checklist.sections
    ]

    return ChecklistSchemaResponse(
        screening_id=sid,
        total_items=checklist.total_items,
        sections=sections,
        generated_at=checklist.generated_at,
    )
