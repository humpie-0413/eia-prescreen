"""유사 사례 검색 · LLM 해석 · PDF 리포트 API 엔드포인트."""

import io
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from backend.app.core.database import check_db_connection, get_session
from backend.app.core.rate_limiter import limiter, LIMIT_LLM, LIMIT_PDF
from backend.app.services.case_search import CaseSearchService
from backend.app.services.llm_interpreter import LLMInterpreter
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.checklist_generator import ChecklistGenerator
from backend.app.schemas.cases import (
    CaseResponse,
    CaseSearchResponse,
    InterpretationResponse,
    ReportRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()            # /api/cases prefix
screening_router = APIRouter()  # /api/screening prefix

# ── 서비스 인스턴스 ──

_case_search = CaseSearchService()
_llm_interpreter = LLMInterpreter()
_report_gen = ReportGenerator()
_checklist_gen = ChecklistGenerator()


# ──────────────────────────────────────────────────────────
# GET /api/cases — 사례 검색
# ──────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=CaseSearchResponse,
    summary="사례 검색",
    description="프로젝트 유형, 입지유형, 키워드, 태그 기반으로 과거 환경영향평가 사례를 검색한다.",
)
async def search_cases(
    project_type: str | None = Query(None, description="사업유형 필터"),
    location_type: str | None = Query(None, description="입지유형 필터"),
    keyword: str | None = Query(None, description="키워드 검색 (summary, key_issues, tags)"),
    tags: str | None = Query(None, description="태그 필터 (쉼표 구분)"),
    limit: int = Query(10, ge=1, le=50, description="최대 반환 건수"),
) -> CaseSearchResponse:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    result = _case_search.search(
        project_type=project_type,
        location_type=location_type,
        keyword=keyword,
        tags=tag_list,
        limit=limit,
    )

    cases = [
        CaseResponse(
            case_id=r.case_id,
            project_name=r.project_name,
            year=r.year,
            project_type=r.project_type,
            location_type=r.location_type,
            region=r.region,
            key_issues=r.key_issues,
            remediation_required=r.remediation_required,
            public_concerns=r.public_concerns,
            consultation_result=r.consultation_result or "",
            source_document=r.source_document or "",
            summary=r.summary or "",
            tags=r.tags,
            lessons_learned=r.lessons_learned,
            similarity_score=r.similarity_score,
        )
        for r in result.results
    ]

    return CaseSearchResponse(cases=cases, total=result.total)


# ──────────────────────────────────────────────────────────
# GET /api/cases/{case_id} — 단일 사례 조회
# ──────────────────────────────────────────────────────────


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="단일 사례 조회",
    description="case_id로 특정 사례를 조회한다.",
)
async def get_case(case_id: str) -> CaseResponse:
    for case in _case_search.cases:
        if case.get("case_id") == case_id:
            r = _case_search._to_case_result(case)
            return CaseResponse(
                case_id=r.case_id,
                project_name=r.project_name,
                year=r.year,
                project_type=r.project_type,
                location_type=r.location_type,
                region=r.region,
                key_issues=r.key_issues,
                remediation_required=r.remediation_required,
                public_concerns=r.public_concerns,
                consultation_result=r.consultation_result or "",
                source_document=r.source_document or "",
                summary=r.summary or "",
                tags=r.tags,
                lessons_learned=r.lessons_learned,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case {case_id} not found",
    )


# ──────────────────────────────────────────────────────────
# POST /api/screening/{id}/similar-cases — 유사 사례 추천
# ──────────────────────────────────────────────────────────


@screening_router.post(
    "/{screening_id}/similar-cases",
    response_model=CaseSearchResponse,
    summary="유사 사례 추천",
    description="스크리닝 리스크 카드 태그를 기반으로 유사 과거 사례를 추천한다.",
)
async def find_similar_cases(
    screening_id: UUID,
    limit: int = Query(5, ge=1, le=20, description="최대 반환 건수"),
) -> CaseSearchResponse:
    from backend.app.services import screening_store

    db_ok = await check_db_connection()

    tags: list[str] = []
    project_type_value: str = "other"

    # Try in-memory store first (works in demo mode)
    record = await screening_store.get(str(screening_id))
    if record:
        project_type_value = record.get("project_type", "other")
        # Extract tags from stored risk cards
        for card in record.get("risk_cards", []):
            if isinstance(card, dict):
                if card.get("title"):
                    tags.append(card["title"])
                if card.get("legal_basis"):
                    tags.append(card["legal_basis"])
            else:
                if getattr(card, "title", None):
                    tags.append(card.title)
                if getattr(card, "legal_basis", None):
                    tags.append(card.legal_basis)
    elif db_ok:
        from backend.app.models.screening import ScreeningRequest

        session_gen = get_session()
        session: AsyncSession = await session_gen.__anext__()
        try:
            stmt = (
                select(ScreeningRequest)
                .where(ScreeningRequest.id == screening_id)
                .options(selectinload(ScreeningRequest.risk_cards))
            )
            result = await session.execute(stmt)
            screening = result.scalar_one_or_none()

            if screening is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Screening {screening_id} not found",
                )

            for card in screening.risk_cards:
                if card.title:
                    tags.append(card.title)
                if card.legal_basis:
                    tags.append(card.legal_basis)

            project_type_value = screening.project_type.value
        finally:
            await session_gen.aclose()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening {screening_id} not found",
        )

    similar = _case_search.find_similar(
        risk_card_tags=tags,
        project_type=project_type_value,
        limit=limit,
    )

    cases = [
        CaseResponse(
            case_id=r.case_id,
            project_name=r.project_name,
            year=r.year,
            project_type=r.project_type,
            location_type=r.location_type,
            region=r.region,
            key_issues=r.key_issues,
            remediation_required=r.remediation_required,
            public_concerns=r.public_concerns,
            consultation_result=r.consultation_result or "",
            source_document=r.source_document or "",
            summary=r.summary or "",
            tags=r.tags,
            lessons_learned=r.lessons_learned,
            similarity_score=r.similarity_score,
        )
        for r in similar.results
    ]

    return CaseSearchResponse(cases=cases, total=similar.total)


# ──────────────────────────────────────────────────────────
# POST /api/screening/{id}/interpret — LLM 해석
# ──────────────────────────────────────────────────────────


@screening_router.post(
    "/{screening_id}/interpret",
    response_model=InterpretationResponse,
    summary="LLM 종합 해석",
    description="리스크 카드 + 규제 매칭 결과를 Gemini 2.0 Flash로 자연어 해석한다.",
)
@limiter.limit(LIMIT_LLM)
async def interpret_screening(
    request: Request,
    screening_id: UUID,
) -> InterpretationResponse:
    from backend.app.services import screening_store

    db_ok = await check_db_connection()

    risk_dicts: list[dict] = []
    reg_dicts: list[dict] = []
    screening_obj = None
    found = False

    # 1) 인메모리/파일 스토어에서 먼저 조회
    record = await screening_store.get(str(screening_id))
    if record:
        found = True
        for card in record.get("risk_cards", []):
            if isinstance(card, dict):
                risk_dicts.append({
                    "rule_id": card.get("rule_id", ""),
                    "title": card.get("title", ""),
                    "severity": card.get("severity", ""),
                    "rationale": card.get("rationale", ""),
                    "evidence": card.get("evidence", ""),
                    "next_action": card.get("next_action", ""),
                    "legal_basis": card.get("legal_basis", ""),
                })
            else:
                risk_dicts.append({
                    "rule_id": getattr(card, "rule_id", ""),
                    "title": getattr(card, "title", ""),
                    "severity": getattr(card, "severity", ""),
                    "rationale": getattr(card, "rationale", ""),
                    "evidence": getattr(card, "evidence", ""),
                    "next_action": getattr(card, "next_action", ""),
                    "legal_basis": getattr(card, "legal_basis", ""),
                })

        for reg in record.get("regulation_matches", []):
            if isinstance(reg, dict):
                reg_dicts.append({
                    "regulation_name": reg.get("regulation_name", ""),
                    "regulation_code": reg.get("regulation_code", ""),
                    "legal_basis": reg.get("legal_basis", ""),
                    "description": reg.get("description", ""),
                    "restriction_level": reg.get("restriction_level", ""),
                    "permit_required": reg.get("permit_required"),
                    "related_authority": reg.get("related_authority", ""),
                })
            else:
                reg_dicts.append({
                    "regulation_name": getattr(reg, "regulation_name", ""),
                    "regulation_code": getattr(reg, "regulation_code", ""),
                    "legal_basis": getattr(reg, "legal_basis", ""),
                    "description": getattr(reg, "description", ""),
                    "restriction_level": getattr(reg, "restriction_level", ""),
                    "permit_required": getattr(reg, "permit_required", None),
                    "related_authority": getattr(reg, "related_authority", ""),
                })

    # 2) 인메모리에 없으면 DB 조회
    if not found and db_ok:
        from backend.app.models.screening import ScreeningRequest

        session_gen = get_session()
        session: AsyncSession = await session_gen.__anext__()
        try:
            stmt = (
                select(ScreeningRequest)
                .where(ScreeningRequest.id == screening_id)
                .options(
                    selectinload(ScreeningRequest.risk_cards),
                    selectinload(ScreeningRequest.regulation_matches),
                )
            )
            result = await session.execute(stmt)
            screening_obj = result.scalar_one_or_none()

            if screening_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Screening {screening_id} not found",
                )

            found = True
            risk_dicts = [
                {
                    "rule_id": c.rule_id,
                    "title": c.title,
                    "severity": c.severity.value,
                    "rationale": c.rationale,
                    "evidence": c.evidence,
                    "next_action": c.next_action,
                    "legal_basis": c.legal_basis,
                }
                for c in screening_obj.risk_cards
            ]

            reg_dicts = [
                {
                    "regulation_name": r.regulation_name,
                    "regulation_code": r.regulation_code,
                    "legal_basis": r.legal_basis,
                    "description": r.description,
                    "restriction_level": r.restriction_level,
                    "permit_required": r.permit_required,
                    "related_authority": r.related_authority,
                }
                for r in screening_obj.regulation_matches
            ]
        finally:
            await session_gen.aclose()

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening {screening_id} not found",
        )

    # LLM 해석 실행
    interpretation_result = await _llm_interpreter.interpret(
        risk_cards=risk_dicts,
        regulation_matches=reg_dicts,
    )

    # 해석 결과를 인메모리 스토어에도 저장
    if record is not None:
        record["llm_interpretation"] = interpretation_result["interpretation"]
        await screening_store.update_evaluation(
            str(screening_id),
            record.get("risk_cards", []),
            record.get("regulation_matches", []),
        )

    # 해석 결과를 DB에 저장 (DB 사용 가능하고 screening이 있을 때만)
    if db_ok and screening_obj is not None:
        session_gen = get_session()
        session = await session_gen.__anext__()
        try:
            from backend.app.models.screening import ScreeningRequest

            stmt = select(ScreeningRequest).where(ScreeningRequest.id == screening_id)
            result = await session.execute(stmt)
            s = result.scalar_one_or_none()
            if s:
                s.llm_interpretation = interpretation_result["interpretation"]
                await session.commit()
        finally:
            await session_gen.aclose()

    return InterpretationResponse(
        interpretation=interpretation_result["interpretation"],
        model=interpretation_result["model"],
        generated_at=interpretation_result["generated_at"],
        disclaimer=interpretation_result["disclaimer"],
        ai_generated=interpretation_result["ai_generated"],
    )


# ──────────────────────────────────────────────────────────
# POST /api/screening/{id}/report — PDF 리포트 생성
# ──────────────────────────────────────────────────────────


@screening_router.post(
    "/{screening_id}/report",
    summary="PDF 리포트 생성",
    description="스크리닝 결과를 PDF 리포트로 생성한다. brief(1p), full(5-10p), checklist 중 선택.",
    responses={200: {"content": {"application/pdf": {}}}},
)
@limiter.limit(LIMIT_PDF)
async def generate_report(
    request: Request,
    screening_id: UUID,
    body: ReportRequest,
) -> StreamingResponse:
    from backend.app.services import screening_store

    db_ok = await check_db_connection()

    project_info: dict = {
        "project_name": "Demo Project",
        "project_type": "other",
        "project_scale": "",
        "address": "",
    }
    risk_dicts: list[dict] = []
    reg_dicts: list[dict] = []
    interpretation: str = ""
    project_type_value: str = "other"
    found = False

    # 1) 인메모리/파일 스토어에서 먼저 조회
    record = await screening_store.get(str(screening_id))
    if record:
        found = True
        project_info = {
            "project_name": record.get("project_name", ""),
            "project_type": record.get("project_type", "other"),
            "project_scale": record.get("project_scale", ""),
            "address": record.get("address", ""),
        }
        project_type_value = record.get("project_type", "other")
        interpretation = record.get("llm_interpretation", "") or ""

        for card in record.get("risk_cards", []):
            if isinstance(card, dict):
                risk_dicts.append({
                    "rule_id": card.get("rule_id", ""),
                    "title": card.get("title", ""),
                    "severity": card.get("severity", ""),
                    "rationale": card.get("rationale", ""),
                    "evidence": card.get("evidence", ""),
                    "next_action": card.get("next_action", ""),
                    "legal_basis": card.get("legal_basis", ""),
                })
            else:
                risk_dicts.append({
                    "rule_id": getattr(card, "rule_id", ""),
                    "title": getattr(card, "title", ""),
                    "severity": getattr(card, "severity", ""),
                    "rationale": getattr(card, "rationale", ""),
                    "evidence": getattr(card, "evidence", ""),
                    "next_action": getattr(card, "next_action", ""),
                    "legal_basis": getattr(card, "legal_basis", ""),
                })

        for reg in record.get("regulation_matches", []):
            if isinstance(reg, dict):
                reg_dicts.append({
                    "regulation_name": reg.get("regulation_name", ""),
                    "regulation_code": reg.get("regulation_code", ""),
                    "legal_basis": reg.get("legal_basis", ""),
                    "description": reg.get("description", ""),
                    "restriction_level": reg.get("restriction_level", ""),
                    "permit_required": reg.get("permit_required"),
                    "related_authority": reg.get("related_authority", ""),
                })
            else:
                reg_dicts.append({
                    "regulation_name": getattr(reg, "regulation_name", ""),
                    "regulation_code": getattr(reg, "regulation_code", ""),
                    "legal_basis": getattr(reg, "legal_basis", ""),
                    "description": getattr(reg, "description", ""),
                    "restriction_level": getattr(reg, "restriction_level", ""),
                    "permit_required": getattr(reg, "permit_required", None),
                    "related_authority": getattr(reg, "related_authority", ""),
                })

    # 2) 인메모리에 없으면 DB 조회
    if not found and db_ok:
        from backend.app.models.screening import ScreeningRequest

        session_gen = get_session()
        session: AsyncSession = await session_gen.__anext__()
        try:
            stmt = (
                select(ScreeningRequest)
                .where(ScreeningRequest.id == screening_id)
                .options(
                    selectinload(ScreeningRequest.risk_cards),
                    selectinload(ScreeningRequest.regulation_matches),
                )
            )
            result = await session.execute(stmt)
            screening = result.scalar_one_or_none()

            if screening is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Screening {screening_id} not found",
                )

            found = True
            project_info = {
                "project_name": screening.project_name,
                "project_type": screening.project_type.value,
                "project_scale": screening.project_scale,
                "address": screening.address,
            }
            project_type_value = screening.project_type.value

            risk_dicts = [
                {
                    "rule_id": c.rule_id,
                    "title": c.title,
                    "severity": c.severity.value,
                    "rationale": c.rationale,
                    "evidence": c.evidence,
                    "next_action": c.next_action,
                    "legal_basis": c.legal_basis,
                }
                for c in screening.risk_cards
            ]

            reg_dicts = [
                {
                    "regulation_name": r.regulation_name,
                    "regulation_code": r.regulation_code,
                    "legal_basis": r.legal_basis,
                    "description": r.description,
                    "restriction_level": r.restriction_level,
                    "permit_required": r.permit_required,
                    "related_authority": r.related_authority,
                }
                for r in screening.regulation_matches
            ]

            interpretation = screening.llm_interpretation or ""
        finally:
            await session_gen.aclose()

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening {screening_id} not found",
        )

    # 체크리스트 생성
    checklist_result = _checklist_gen.generate(
        risk_dicts, reg_dicts, screening_id=str(screening_id)
    )
    checklist_pdf_data = _checklist_gen.to_pdf_structure(checklist_result)

    # 리포트 유형에 따라 PDF 생성
    report_type = body.report_type

    if report_type == "brief":
        pdf_bytes = _report_gen.generate_brief(
            project_info=project_info,
            risk_cards=risk_dicts,
            regulations=reg_dicts,
            interpretation=interpretation,
        )
        filename = f"eia_brief_{screening_id}.pdf"

    elif report_type == "full":
        # 유사 사례 조회
        tags: list[str] = []
        for rd in risk_dicts:
            if rd.get("title"):
                tags.append(rd["title"])
            if rd.get("legal_basis"):
                tags.append(rd["legal_basis"])

        similar = _case_search.find_similar(
            risk_card_tags=tags,
            project_type=project_type_value,
            limit=5,
        )
        cases = [r.model_dump() for r in similar.results]

        pdf_bytes = _report_gen.generate_full_report(
            project_info=project_info,
            risk_cards=risk_dicts,
            regulations=reg_dicts,
            cases=cases,
            interpretation=interpretation,
            checklist=checklist_pdf_data,
        )
        filename = f"eia_full_report_{screening_id}.pdf"

    else:  # checklist
        pdf_bytes = _report_gen.generate_checklist_pdf(
            checklist=checklist_pdf_data,
        )
        filename = f"eia_checklist_{screening_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
