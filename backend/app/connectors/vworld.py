"""V-world WFS 연속지적도 커넥터 (B계층 — 불안정형+캐시).

데이터 소스: V-world WFS/연속지적도 GetFeature
https://www.vworld.kr/
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


class VworldConnector(BaseConnector):
    name = "vworld"
    tier = DataTier.B
    description = "V-world WFS 연속지적도 — 필지 경계·지목·면적 조회"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.VWORLD_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://api.vworld.kr/req/wfs",
                    params={
                        "key": api_key,
                        "service": "WFS",
                        "version": "2.0.0",
                        "request": "GetFeature",
                        "typeName": "lp_pa_cbnd_bonbun",
                        "bbox": f"{lng-0.01},{lat-0.01},{lng+0.01},{lat+0.01}",
                        "srsName": "EPSG:4326",
                        "output": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("V-world API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

