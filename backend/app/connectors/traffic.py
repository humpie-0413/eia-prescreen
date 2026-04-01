"""교통 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 한국도로공사 실시간 전국 교통량 OpenAPI
- URL: https://data.ex.co.kr/openapi/trafficapi/trafficAll
- 전국 고속도로 실시간 교통량 (1시간/15분/5분 집계)
- 차종별(1~8종), TCS/하이패스 구분, 도공/민자 구분
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

_TRAFFIC_URL = "https://data.ex.co.kr/openapi/trafficapi/trafficAll"


class TrafficConnector(BaseConnector):
    name = "traffic"
    tier = DataTier.B
    description = "한국도로공사 실시간 교통량 — 고속도로 차종별·구간별 교통량"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.DATA_EX_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    _TRAFFIC_URL,
                    params={
                        "key": api_key,
                        "type": "json",
                        "tmType": "1",  # 1시간 집계
                    },
                )
                resp.raise_for_status()
                raw = resp.json()

            # 응답 파싱
            data = self._parse_response(raw)

            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Traffic API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    # 차종코드 → 라벨
    _CAR_TYPES: dict[str, str] = {
        "1": "1종(소형)", "2": "2종(중형)", "3": "3종(대형)",
        "4": "4종(대형화물)", "5": "5종(특수)", "6": "6종(경차)",
        "7": "7종(소형화물)", "8": "8종(기타)",
    }

    def _parse_response(self, raw: dict) -> dict[str, Any]:
        """API 응답을 정규화된 데이터로 변환한다."""
        items = []
        total_traffic = 0
        by_car_type: dict[str, int] = {}

        # 응답 구조: {"count": N, "trafficAll": [{...}, ...]}
        result_list = raw.get("trafficAll", [])
        if isinstance(result_list, list):
            for item in result_list:
                if not isinstance(item, dict):
                    continue
                traffic_amount = int(item.get("trafficAmout", 0) or 0)
                total_traffic += traffic_amount

                car_code = item.get("carType", "")
                car_label = self._CAR_TYPES.get(car_code, car_code)
                by_car_type[car_label] = by_car_type.get(car_label, 0) + traffic_amount

                items.append({
                    "division": item.get("exDivName", ""),
                    "data_type": item.get("tmName", ""),
                    "tcs_type": item.get("tcsName", ""),
                    "traffic_amount": traffic_amount,
                    "aggregation_time": item.get("sumTm", ""),
                    "aggregation_date": item.get("sumDate", ""),
                    "car_type": car_label,
                })

        return {
            "source": "한국도로공사 실시간 교통량",
            "total_traffic": total_traffic,
            "record_count": int(raw.get("count", len(items))),
            "by_car_type": by_car_type,
            "records": items[:30],  # 상위 30건
        }

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")
