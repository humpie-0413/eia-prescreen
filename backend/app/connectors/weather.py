"""기상 커넥터 (A계층 — 안정형 실시간).

데이터 소스: 기상청 종관기상관측(ASOS)
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


class WeatherConnector(BaseConnector):
    name = "weather"
    tier = DataTier.A
    description = "기상청 종관기상관측(ASOS) — 기온·강수·풍속·일조"

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
                    "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
                    params={
                        "serviceKey": api_key,
                        "dataType": "JSON",
                        "dataCd": "ASOS",
                        "dateCd": "DAY",
                        "startDt": "20250101",
                        "endDt": "20250107",
                        "stnIds": "108",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            parsed = self._parse_weather(data)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", parsed)
            return self._make_result(parsed)

        except Exception as e:
            logger.warning("Weather API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    def _parse_weather(self, raw: dict) -> dict:
        """ASOS API 응답에서 기온·강수·풍속·일조·일사 필드 추출."""
        items = (
            raw.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]

        result = {**raw}
        if items:
            last = items[-1] if items else {}
            result["sunshine_hours"] = self._safe_float(last.get("sumSsHr"))
            result["solar_radiation"] = self._safe_float(last.get("sumGsr"))  # icsr or sumGsr
        else:
            result["sunshine_hours"] = None
            result["solar_radiation"] = None
        return result

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

