"""위락시설 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: V-world WFS POI 레이어 또는 CSV 폴백
"""

import logging
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


class FacilitiesConnector(BaseConnector):
    name = "facilities"
    tier = DataTier.B
    description = "위락시설 POI — 관광·위락·체육시설 분포"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = getattr(settings, "VWORLD_API_KEY", "") or ""
        if not api_key:
            return self._make_empty_data()

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://api.vworld.kr/req/data",
                    params={
                        "key": api_key,
                        "service": "data",
                        "request": "GetFeature",
                        "data": "LT_C_TODOPOI",
                        "geomFilter": f"POINT({lng} {lat})",
                        "buffer": str(int(buffer_m)),
                        "format": "json",
                        "size": "20",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            data = self._parse(raw)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Facilities API failed: %s — trying cache", e)
            cached, freshness = self._cache.load_snapshot(self.name)
            if cached:
                return self._make_result(cached, ConnectorStatus.UNSTABLE, freshness)
            return self._make_empty_data()

    def _parse(self, raw: dict) -> dict:
        """API 응답 파싱."""
        return {
            "recreation_facility_count": 0,
            "recreation_facility_distance_m": None,
            "recreation_density_area": False,
        }

    def _make_empty_data(self) -> ConnectorResult:
        return self._make_result({
            "recreation_facility_count": 0,
            "recreation_facility_distance_m": None,
            "recreation_density_area": False,
        })
