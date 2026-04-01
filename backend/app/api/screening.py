from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.screening import (
    ScreeningInput,
    ScreeningResponse,
    ScreeningSummary,
)
from backend.app.services import screening_store

router = APIRouter()


@router.post(
    "",
    response_model=ScreeningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 스크리닝 요청 생성",
)
async def create_screening(body: ScreeningInput) -> ScreeningResponse:
    data = {
        "project_name": body.project_name,
        "project_type": body.project_type,
        "project_scale": body.project_scale,
        "address": body.address,
        "lng": body.location.lng if body.location else None,
        "lat": body.location.lat if body.location else None,
    }
    record = await screening_store.create(data)
    return ScreeningResponse(**record)


@router.get(
    "/{screening_id}",
    response_model=ScreeningResponse,
    summary="스크리닝 결과 조회",
)
async def get_screening(screening_id: str) -> ScreeningResponse:
    record = await screening_store.get(screening_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Screening not found")
    return ScreeningResponse(**record)


@router.get(
    "",
    response_model=list[ScreeningSummary],
    summary="스크리닝 목록 조회",
)
async def list_screenings() -> list[ScreeningSummary]:
    items = await screening_store.list_all()
    summaries: list[ScreeningSummary] = []
    for data in items:
        cards = data.get("risk_cards", [])
        summaries.append(
            ScreeningSummary(
                id=data["id"],
                project_name=data["project_name"],
                project_type=data.get("project_type", "other"),
                status=data.get("status", "pending"),
                created_at=data["created_at"],
                risk_card_count=len(cards),
                critical_count=sum(
                    1
                    for r in cards
                    if (r.get("severity") if isinstance(r, dict) else getattr(r, "severity", None))
                    in ("critical",)
                ),
                major_count=sum(
                    1
                    for r in cards
                    if (r.get("severity") if isinstance(r, dict) else getattr(r, "severity", None))
                    in ("major",)
                ),
            )
        )
    return summaries
