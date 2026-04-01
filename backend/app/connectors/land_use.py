"""토지이용규제정보 커넥터 (A계층 — 안정형 실시간).

데이터 소스:
- 1차: 토지이용규제정보서비스(토지이음) API
- 2차: V-world Data API — 용도지역·개발제한구역·토지이용계획·하천·유역 등
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

_VWORLD_DATA_URL = "https://api.vworld.kr/req/data"

# 테스트 검증 완료된 V-world Data API 레이어 목록
_VWORLD_LAYERS: dict[str, str] = {
    # 용도지역
    "LT_C_UQ111": "도시지역",
    "LT_C_UQ112": "관리지역",
    "LT_C_UQ113": "농림지역",
    "LT_C_UQ114": "자연환경보전지역",
    "LT_C_UQ141": "개발제한구역(그린벨트)",
    # 토지이용·건물
    "LT_C_LHBLPN": "토지이용계획",
    "LT_C_SPBD": "건물",
    # 수계
    "LT_C_WKMBBSN": "유역권역",
    "LT_C_WKMSTRM": "하천",
    # 보호구역 (위치에 따라 NODATA 가능)
    "LT_C_AISRESC": "문화재보호구역",
    "LT_C_DAMDAN": "댐",
}


class LandUseConnector(BaseConnector):
    name = "land_use"
    tier = DataTier.A
    description = "토지이용규제정보서비스(토지이음) — 용도지역·용도지구·용도구역 조회"

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
            logger.warning("DATA_GO_KR_API_KEY not set - returning cached data")
            data, freshness = self._cache.load_snapshot(self.name)
            if data:
                return self._make_result(data, ConnectorStatus.STABLE, freshness)
            return self._make_error("API key not configured and no cache available")

        land_use_data: dict | None = None

        # 1차: 토지이용규제정보 API
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://apis.data.go.kr/1613000/arLandUseInfoService/DTarLandUseInfo",
                    params={
                        "serviceKey": api_key,
                        "numOfRows": 10,
                        "pageNo": 1,
                        "type": "json",
                    },
                )
                resp.raise_for_status()
                land_use_data = resp.json()
        except Exception as e:
            logger.info("Land use API failed: %s - trying V-world supplement", e)

        # 2차 보충: V-world 전체 레이어 조회 (VWORLD_API_KEY 필요)
        vworld_data = await self._fetch_vworld_layers(lng, lat, buffer_m)

        # 결과 병합
        if land_use_data:
            if vworld_data:
                land_use_data["vworld"] = vworld_data
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", land_use_data)
            return self._make_result(land_use_data)

        if vworld_data:
            data = {"vworld": vworld_data}
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data, ConnectorStatus.UNSTABLE)

        # 캐시 폴백
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error("Land use APIs unavailable and no cache")

    async def _fetch_vworld_layers(
        self, lng: float, lat: float, buffer_m: float
    ) -> dict | None:
        """V-world Data API에서 검증된 레이어를 일괄 조회한다."""
        vworld_key = settings.VWORLD_API_KEY
        if not vworld_key:
            return None

        result: dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                for layer_code, layer_name in _VWORLD_LAYERS.items():
                    try:
                        resp = await client.get(
                            _VWORLD_DATA_URL,
                            params={
                                "key": vworld_key,
                                "service": "data",
                                "request": "GetFeature",
                                "data": layer_code,
                                "geomFilter": f"POINT({lng} {lat})",
                                "buffer": int(buffer_m),
                                "domain": "localhost",
                                "size": 10,
                                "page": 1,
                            },
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        vw_resp = data.get("response", {})
                        status = vw_resp.get("status", "")

                        if status == "OK":
                            features = (
                                vw_resp.get("result", {})
                                .get("featureCollection", {})
                                .get("features", [])
                            )
                            result[layer_code] = {
                                "name": layer_name,
                                "found": True,
                                "count": len(features),
                                "features": [
                                    f.get("properties", {}) for f in features[:5]
                                ],
                            }
                        else:
                            result[layer_code] = {
                                "name": layer_name,
                                "found": False,
                            }
                    except Exception as e:
                        logger.debug("V-world %s failed: %s", layer_code, e)

        except Exception as e:
            logger.warning("V-world layer batch failed: %s", e)
            return None

        return result if result else None

