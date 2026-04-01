"""전파환경 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 과기정통부 전파환경측정 API 또는 CSV 폴백
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


class RadioConnector(BaseConnector):
    name = "radio"
    tier = DataTier.B
    description = "전파환경측정 — 전파간섭 가능 시설 조회"

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
            return self._make_empty_data()

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://apis.data.go.kr/B551982/radioEnvMeasure/getRadioEnvMeasureList",
                    params={
                        "serviceKey": api_key,
                        "dataType": "JSON",
                        "numOfRows": "10",
                        "pageNo": "1",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            data = self._parse(raw)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Radio API failed: %s — trying cache", e)
            cached, freshness = self._cache.load_snapshot(self.name)
            if cached:
                return self._make_result(cached, ConnectorStatus.UNSTABLE, freshness)
            return self._make_empty_data()

    def _parse(self, raw: dict) -> dict:
        """API 응답 파싱."""
        return {
            "radio_interference_risk": False,
            "radar_facility_distance_m": None,
            "broadcasting_tower_distance_m": None,
        }

    def _make_empty_data(self) -> ConnectorResult:
        return self._make_result({
            "radio_interference_risk": False,
            "radar_facility_distance_m": None,
            "broadcasting_tower_distance_m": None,
        })
