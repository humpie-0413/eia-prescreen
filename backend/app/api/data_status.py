"""데이터 가용성 API 엔드포인트."""

from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Query

from backend.app.connectors.base import ConnectorResult, ConnectorStatus as CStatus
from backend.app.core.config import settings
from backend.app.schemas.data_status import (
    ConnectorFreshnessResponse,
    ConnectorListResponse,
    ConnectorStatusResponse,
    ScreeningDataStatusResponse,
)
from backend.app.services import screening_store
from backend.app.services.data_fetcher import DataFetcher

router = APIRouter()

_fetcher = DataFetcher()


def _build_connector_response(
    name: str,
    tier: str,
    description: str,
    result: ConnectorResult | None,
) -> ConnectorStatusResponse:
    """ConnectorResult를 응답 스키마로 변환한다."""
    if result is None:
        return ConnectorStatusResponse(
            name=name,
            tier=tier,
            description=description,
            status="unknown",
            has_data=False,
        )

    freshness = None
    last_success_at = None
    if result.freshness:
        freshness = ConnectorFreshnessResponse(
            fetched_at=result.freshness.fetched_at,
            snapshot_at=result.freshness.snapshot_at,
            fallback_used=result.freshness.fallback_used,
            freshness=result.freshness.freshness,
        )
        last_success_at = result.freshness.fetched_at or result.freshness.snapshot_at

    return ConnectorStatusResponse(
        name=result.connector_name,
        tier=result.tier,
        description=description,
        status=result.status.value,
        freshness=freshness,
        has_data=result.data is not None,
        error=result.error,
        last_success_at=last_success_at,
    )


def _build_status_response(
    results: dict[str, ConnectorResult],
    screening_id: str | None = None,
) -> ScreeningDataStatusResponse:
    """fetch 결과를 ScreeningDataStatusResponse로 변환한다."""
    connector_responses: list[ConnectorStatusResponse] = []
    for conn in _fetcher.connectors:
        r = results.get(conn.name)
        connector_responses.append(
            _build_connector_response(conn.name, conn.tier.value, conn.description, r)
        )

    total = len(connector_responses)
    available = sum(1 for c in connector_responses if c.has_data)
    coverage_pct = round((available / total) * 100, 1) if total > 0 else 0.0

    freshness_counter: Counter[str] = Counter()
    for c in connector_responses:
        level = c.freshness.freshness if c.freshness else "unknown"
        freshness_counter[level] += 1

    return ScreeningDataStatusResponse(
        screening_id=screening_id,
        connectors=connector_responses,
        total=total,
        available=available,
        coverage_pct=coverage_pct,
        freshness_summary=dict(freshness_counter),
    )


# ──────────────────────────────────────────────────────────
# 주의: /connectors 가 /{screening_id} 보다 먼저 등록되어야
#       FastAPI가 "connectors"를 UUID로 파싱하지 않는다.
# ──────────────────────────────────────────────────────────


@router.get(
    "/connectors",
    response_model=ConnectorListResponse,
    summary="전체 커넥터 목록과 현재 상태",
    description="등록된 모든 데이터 커넥터의 이름, 계층, 설명, 현재 상태를 반환한다.",
)
async def list_connectors() -> ConnectorListResponse:
    connector_list: list[ConnectorStatusResponse] = []
    for conn in _fetcher.connectors:
        connector_list.append(
            ConnectorStatusResponse(
                name=conn.name,
                tier=conn.tier.value,
                description=conn.description,
                status="unknown",
                has_data=False,
            )
        )
    return ConnectorListResponse(
        connectors=connector_list,
        total=len(connector_list),
    )


@router.get(
    "/{screening_id}",
    response_model=ScreeningDataStatusResponse,
    summary="스크리닝별 데이터 상태",
    description=(
        "특정 스크리닝에 대해 커넥터별 상태, 신선도, 데이터 존재 여부, "
        "전체 커버리지 퍼센트를 반환한다."
    ),
)
async def get_screening_data_status(
    screening_id: UUID,
) -> ScreeningDataStatusResponse:
    sid = str(screening_id)
    record = await screening_store.get(sid)

    lng = record.get("lng") if record else None
    lat = record.get("lat") if record else None

    if lng is None or lat is None:
        # 좌표가 없으면 빈 결과 반환
        return _build_status_response({}, sid)

    results = await _fetcher.fetch_all(lng, lat)
    return _build_status_response(results, sid)


@router.get(
    "",
    response_model=ScreeningDataStatusResponse,
    summary="커넥터별 데이터 상태 대시보드",
    description="각 데이터 커넥터의 현재 상태, 신선도, 오류 여부를 반환한다.",
)
async def get_data_status(
    lng: float = Query(127.49, description="경도"),
    lat: float = Query(37.49, description="위도"),
) -> ScreeningDataStatusResponse:
    results = await _fetcher.fetch_all(lng, lat)
    return _build_status_response(results)
