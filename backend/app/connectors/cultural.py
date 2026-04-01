"""문화재 커넥터 (C계층 — 수동 스냅샷/큐레이션).

데이터 소스: 문화재청 GIS 서비스
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


class CulturalConnector(BaseConnector):
    name = "cultural"
    tier = DataTier.C
    description = "문화재청 GIS — 문화재 보호구역·매장문화재 분포"

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
                    "https://apis.data.go.kr/1360000/CulturalHeritage/getListCulturalHeritage",
                    params={
                        "serviceKey": api_key,
                        "lng": lng,
                        "lat": lat,
                        "buffer": buffer_m,
                        "returnType": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Cultural Heritage API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

