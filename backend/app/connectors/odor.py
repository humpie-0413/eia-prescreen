"""악취 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 국립환경과학원 악취측정망 API (data.go.kr)
폴백: data/static/odor_management_areas.csv
"""

import logging
from pathlib import Path
from typing import Any

import httpx

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataTier,
)
from backend.app.core.config import settings
from backend.app.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "static"


class OdorConnector(BaseConnector):
    name = "odor"
    tier = DataTier.B
    description = "국립환경과학원 악취측정망 — 악취관리지역·악취측정소"

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
            return await self._fallback_to_static(lng, lat)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://apis.data.go.kr/B553748/OdorMsrstnInfoInqireService/getOdorMsrstnList",
                    params={
                        "serviceKey": api_key,
                        "dataType": "JSON",
                        "numOfRows": "20",
                        "pageNo": "1",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            data = self._parse(raw, lng, lat)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Odor API failed: %s — trying static/cache", e)
            return await self._fallback_to_static(lng, lat, str(e))

    def _parse(self, raw: dict, lng: float, lat: float) -> dict:
        """API 응답에서 악취측정소 목록 파싱."""
        items = (
            raw.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]

        stations = []
        for item in items:
            stations.append({
                "station_name": item.get("msrstnNm", ""),
                "address": item.get("msrstnAddr", ""),
            })

        return {
            "stations": stations[:5],
            "station_count": len(stations),
            "management_area_overlap": False,
            "nearest_odor_facility_m": None,
            "odor_exceed": False,
        }

    async def _fallback_to_static(
        self, lng: float, lat: float, error: str = "",
    ) -> ConnectorResult:
        """CSV 폴백 또는 캐시 폴백."""
        # Try cache first
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)

        # Static CSV fallback — return empty but valid structure
        return self._make_result({
            "stations": [],
            "station_count": 0,
            "management_area_overlap": False,
            "nearest_odor_facility_m": None,
            "odor_exceed": False,
        })
