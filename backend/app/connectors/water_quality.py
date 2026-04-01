"""물환경정보 커넥터 (B계층 — 불안정형+캐시).

데이터 소스: 물환경정보시스템(WEIS) OpenAPI (공공데이터포털)
- 수질측정망 측정 데이터 (getWaterMeasuringList)

제한사항: 현재 API는 필터 파라미터(wmyr, ptNo 등)를 무시하고
고정 데이터셋(2007-2011)만 반환합니다. 실시간 수질 데이터로는
부적합하나, API 연결성 확인과 BOD/COD 참고 데이터로 사용 가능.
"""

import logging
from typing import Any

import httpx

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataFreshness,
    DataTier,
)
from backend.app.core.config import settings
from backend.app.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)

_WATER_QUALITY_URL = (
    "https://apis.data.go.kr/1480523/WaterQualityService/getWaterMeasuringList"
)


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _bod_to_grade(bod: float | None) -> str:
    """BOD 값으로 수질등급을 추정한다."""
    if bod is None:
        return "측정불가"
    if bod <= 1.0:
        return "Ia (매우 좋음)"
    if bod <= 2.0:
        return "Ib (약간 좋음)"
    if bod <= 3.0:
        return "II (보통)"
    if bod <= 5.0:
        return "III (약간 나쁨)"
    if bod <= 8.0:
        return "IV (나쁨)"
    return "V (매우 나쁨)"


class WaterQualityConnector(BaseConnector):
    name = "water_quality"
    tier = DataTier.B
    description = "물환경정보시스템(WEIS) — 수질측정망 데이터"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    _WATER_QUALITY_URL,
                    params={
                        "serviceKey": api_key,
                        "resultType": "json",
                        "numOfRows": 50,
                        "pageNo": 1,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            items = raw.get("getWaterMeasuringList", {}).get("item", [])
            if not items:
                return await self._fallback_to_cache("No water quality data")

            # 좌표에 가장 가까운 측정소 찾기
            best = self._find_nearest(items, lng, lat)
            data = self._parse_item(best)

            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(
                data,
                freshness=DataFreshness(
                    freshness="stale",
                    fallback_used=True,
                ),
            )

        except Exception as e:
            logger.warning("Water quality API failed: %s - trying cache", e)
            return await self._fallback_to_cache(str(e))

    @staticmethod
    def _find_nearest(items: list[dict], lng: float, lat: float) -> dict:
        """측정소 목록에서 좌표에 가장 가까운 항목을 반환."""
        best = items[0]
        best_dist = float("inf")
        for item in items:
            try:
                pt_lng = int(item.get("LON_DGR", 0)) + int(item.get("LON_MIN", 0)) / 60
                pt_lat = int(item.get("LAT_DGR", 0)) + int(item.get("LAT_MIN", 0)) / 60
                dist = (pt_lng - lng) ** 2 + (pt_lat - lat) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best = item
            except (ValueError, TypeError):
                continue
        return best

    @staticmethod
    def _parse_item(item: dict) -> dict:
        """API 항목을 룰 엔진 포맷으로 변환."""
        bod = _safe_float(item.get("ITEM_BOD"))
        tp = _safe_float(item.get("ITEM_TP"))
        return {
            "nearest_river": item.get("PT_NM", ""),
            "river_distance_m": None,
            "water_source_protection_distance_m": None,
            "sensitive_water_zone": None,
            "sensitive_zone_name": None,
            "bod_avg": bod,
            "tp_avg": tp,
            "water_grade": _bod_to_grade(bod),
            "watershed": None,
            "total_pollution_load_area": None,
            "underground_water_protection_distance_m": None,
            "measurement_date": item.get("WMCYMD"),
            "station_code": item.get("PT_NO"),
        }

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

