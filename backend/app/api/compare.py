"""부지 비교 API 엔드포인트."""

import io
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from backend.app.core.database import check_db_connection, get_session
from backend.app.core.rate_limiter import limiter, LIMIT_PDF
from backend.app.models.screening import ScreeningRequest
from backend.app.schemas.compare import (
    CompareRequest,
    CompareResponse,
    RiskComparisonRow,
    SiteRiskSummary,
)
from backend.app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

_report_gen = ReportGenerator()


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="부지 비교",
    description="최대 3개 스크리닝 결과를 비교 분석한다.",
)
async def compare_screenings(
    body: CompareRequest,
) -> CompareResponse:
    db_ok = await check_db_connection()
    sites: list[SiteRiskSummary] = []

    if not db_ok:
        # 데모 모드: 빈 비교 결과 반환
        return CompareResponse(sites=[], risk_matrix=[], recommendation="데모 모드에서는 DB 없이 비교 기능이 제한됩니다.")

    session_gen = get_session()
    session: AsyncSession = await session_gen.__anext__()
    try:
        for sid_str in body.screening_ids:
            try:
                sid = UUID(sid_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid UUID: {sid_str}",
                )

            stmt = (
                select(ScreeningRequest)
                .where(ScreeningRequest.id == sid)
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
                    detail=f"Screening {sid_str} not found",
                )

            risk_dicts = [
                {
                    "rule_id": c.rule_id,
                    "title": c.title,
                    "severity": c.severity.value,
                    "rationale": c.rationale,
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
                    "permit_required": r.permit_required,
                    "related_authority": r.related_authority,
                }
                for r in screening.regulation_matches
            ]

            sites.append(SiteRiskSummary(
                screening_id=str(screening.id),
                project_name=screening.project_name,
                project_type=screening.project_type.value,
                address=screening.address,
                total_risks=len(risk_dicts),
                critical_count=sum(1 for r in risk_dicts if r["severity"] == "critical"),
                major_count=sum(1 for r in risk_dicts if r["severity"] == "major"),
                review_count=sum(1 for r in risk_dicts if r["severity"] == "review"),
                info_count=sum(1 for r in risk_dicts if r["severity"] == "info"),
                total_regulations=len(reg_dicts),
                permit_required_count=sum(1 for r in reg_dicts if r.get("permit_required")),
                risk_cards=risk_dicts,
                regulation_matches=reg_dicts,
            ))
    finally:
        await session_gen.aclose()

    # Build risk comparison matrix
    all_rule_ids: dict[str, str] = {}  # rule_id -> title
    for site in sites:
        for card in site.risk_cards:
            all_rule_ids[card["rule_id"]] = card["title"]

    # Sort by severity priority (critical first)
    severity_order = {"critical": 0, "major": 1, "review": 2, "info": 3}

    risk_matrix: list[RiskComparisonRow] = []
    for rule_id, title in sorted(all_rule_ids.items()):
        severity_by_site: dict[str, str | None] = {}
        for site in sites:
            matched = None
            for card in site.risk_cards:
                if card["rule_id"] == rule_id:
                    matched = card["severity"]
                    break
            severity_by_site[site.screening_id] = matched
        risk_matrix.append(RiskComparisonRow(
            rule_id=rule_id,
            title=title,
            severity_by_site=severity_by_site,
        ))

    # Sort matrix: rules that appear in more sites first, then by highest severity
    def matrix_sort_key(row: RiskComparisonRow) -> tuple:
        severities = [v for v in row.severity_by_site.values() if v is not None]
        count = len(severities)
        min_sev = min((severity_order.get(s, 99) for s in severities), default=99)
        return (-count, min_sev, row.rule_id)

    risk_matrix.sort(key=matrix_sort_key)

    # Generate recommendation text
    recommendation = _generate_recommendation(sites)

    return CompareResponse(
        sites=sites,
        risk_matrix=risk_matrix,
        recommendation=recommendation,
    )


def _generate_recommendation(sites: list[SiteRiskSummary]) -> str:
    """Generate a simple text recommendation comparing sites."""
    if not sites:
        return "비교할 부지가 없습니다."

    # Score each site (lower is better)
    scored = []
    for site in sites:
        score = (
            site.critical_count * 10
            + site.major_count * 5
            + site.review_count * 2
            + site.info_count * 1
            + site.permit_required_count * 3
        )
        scored.append((site, score))

    scored.sort(key=lambda x: x[1])
    best = scored[0][0]
    worst = scored[-1][0]

    parts = []
    parts.append(f"비교 분석 결과, {len(sites)}개 부지 중 '{best.project_name}'이(가) "
                 f"상대적으로 환경 리스크가 낮은 것으로 평가됩니다.")

    if len(sites) > 1 and scored[0][1] != scored[-1][1]:
        parts.append(
            f"'{worst.project_name}'은(는) Critical {worst.critical_count}건, "
            f"Major {worst.major_count}건으로 가장 높은 리스크를 보입니다."
        )

    for site, score in scored:
        if site.critical_count > 0:
            parts.append(
                f"'{site.project_name}': Critical 리스크 {site.critical_count}건이 "
                f"있으므로 사업 진행 전 반드시 추가 검토가 필요합니다."
            )

    parts.append("본 비교는 AI 기반 사전검토 결과이며, 최종 판단은 전문가 검토를 통해 이루어져야 합니다.")

    return " ".join(parts)


@router.post(
    "/compare/report",
    summary="부지 비교 보고서 PDF",
    description="부지 비교 결과를 PDF로 생성한다.",
    responses={200: {"content": {"application/pdf": {}}}},
)
@limiter.limit(LIMIT_PDF)
async def compare_report(
    request: Request,
    body: CompareRequest,
) -> StreamingResponse:
    # First get comparison data
    compare_data = await compare_screenings(body)

    pdf_bytes = _report_gen.generate_comparison_report(
        sites=[s.model_dump() for s in compare_data.sites],
        risk_matrix=[r.model_dump() for r in compare_data.risk_matrix],
        recommendation=compare_data.recommendation,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=eia_comparison_report.pdf"},
    )
