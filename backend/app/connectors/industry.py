"""산업 통계 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 통계청 사업체조사 API 또는 CSV 폴백
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


class IndustryConnector(BaseConnector):
    name = "industry"
    tier = DataTier.B
    description = "통계청 사업체조사 — 산업단지·사업체 통계"

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
                    "https://apis.data.go.kr/B190001/service/GetIndustrialComplexInfoService/getIndustrialComplexList",
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
            logger.warning("Industry API failed: %s — trying cache", e)
            cached, freshness = self._cache.load_snapshot(self.name)
            if cached:
                return self._make_result(cached, ConnectorStatus.UNSTABLE, freshness)
            return self._make_empty_data()

    def _parse(self, raw: dict) -> dict:
        """API 응답 파싱."""
        return {
            "industrial_complex_distance_m": None,
            "industrial_complex_name": None,
            "industry_density": None,
        }

    def _make_empty_data(self) -> ConnectorResult:
        return self._make_result({
            "industrial_complex_distance_m": None,
            "industrial_complex_name": None,
            "industry_density": None,
        })
