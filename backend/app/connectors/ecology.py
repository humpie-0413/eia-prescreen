"""생태자연도·보호지역 커넥터 (B계층 — 불안정형+캐시).

데이터 소스:
- 1차: 환경공간정보서비스(EGIS) / 국립생태원 API
- 2차: 환경공간정보 WMS (api.mcee.go.kr, 키 불필요)
       — 토지피복지도 세분류/중분류 + 행정구역
"""

import logging
from typing import Any

import httpx
from pyproj import Transformer

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataTier,
)
from backend.app.core.config import settings
from backend.app.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# ── 좌표 변환 (WGS84 → EPSG:3857 for WMS) ──
_WEB_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

_LANDCOVER_WMS_URL = "https://api.mcee.go.kr/geoserver/wms"

# 토지피복 분류 코드 → 한글 라벨
_LANDCOVER_LABELS = {
    "1": "시가화지역", "2": "농업지역", "3": "산림지역",
    "4": "초지", "5": "습지", "6": "나지", "7": "수역",
}

# 테스트 검증 완료된 환경공간정보 WMS 레이어 (api.mcee.go.kr, 키 불필요)
_WMS_LANDCOVER_LAYERS: list[tuple[str, str]] = [
    ("EGIS:lv2_2000_g", "중분류 토지피복 2000-2004"),
    ("EGIS:lv2_2007_g", "중분류 토지피복 2007"),
    ("EGIS:lv2_2009_g", "중분류 토지피복 2009 수도권/충청"),
    ("EGIS:lv2_2013_g", "중분류 토지피복 2013"),
    ("EGIS:lv2_2018_g", "중분류 토지피복 2018 수도권"),
]

_WMS_ADMIN_LAYER = "EGIS:adm"  # 행정구역 — ADM_CD, ENG_NM, KOR_NM


class EcologyConnector(BaseConnector):
    name = "ecology"
    tier = DataTier.B
    description = "생태자연도·보호지역·멸종위기종 — EGIS/국립생태원"

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

        # 1차: EGIS 생태자연도 API
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                resp = await client.get(
                    "https://apis.data.go.kr/B553084/EcologyzmpService/getEcologyzmpInfo",
                    params={
                        "serviceKey": api_key,
                        "pageNo": 1,
                        "numOfRows": 10,
                        "type": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.info("Ecology EGIS API unavailable: %s - trying WMS fallback", e)

        # 2차: 환경공간정보 WMS (키 불필요 공개 서비스)
        try:
            wms_data = await self._fetch_wms_all(lng, lat, buffer_m)
            if wms_data:
                self._cache.save_snapshot(self.name, f"{lat}_{lng}", wms_data)
                return self._make_result(wms_data)
        except Exception as e:
            logger.warning("WMS also failed: %s - trying cache", e)

        return await self._fallback_to_cache()

    async def _fetch_wms_all(
        self, lng: float, lat: float, buffer_m: float
    ) -> dict | None:
        """환경공간정보 WMS에서 토지피복·행정구역 정보를 일괄 조회한다."""
        x, y = _WEB_MERCATOR.transform(lng, lat)
        half = buffer_m
        bbox = f"{x - half},{y - half},{x + half},{y + half}"

        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=8) as client:
            # 1) 행정구역
            admin = await self._wms_get_feature_info(client, _WMS_ADMIN_LAYER, bbox)
            if admin:
                result["admin"] = admin

            # 2) 토지피복 중분류 (최신 연도 우선)
            for layer_id, layer_desc in reversed(_WMS_LANDCOVER_LAYERS):
                lc = await self._wms_get_feature_info(client, layer_id, bbox)
                if lc:
                    code = str(lc.get("l1_code", ""))[:1]
                    result["landcover"] = {
                        "layer": layer_id,
                        "description": layer_desc,
                        "l1_code": lc.get("l1_code", ""),
                        "l1_name": lc.get("l1_name", ""),
                        "l2_code": lc.get("l2_code", ""),
                        "l2_name": lc.get("l2_name", ""),
                        "landcover_label": _LANDCOVER_LABELS.get(code, "기타"),
                    }
                    break

            # 3) 세분류 토지피복 (기존 EGIS:lv3_2025y 등)
            for lv3 in ("EGIS:lv3_2020_g", "EGIS:lv3_1st_renew_g", "EGIS:lv3_1st_g"):
                lc3 = await self._wms_get_feature_info(client, lv3, bbox)
                if lc3:
                    code = str(lc3.get("LCODE", lc3.get("l1_code", "")))[:1]
                    result["landcover_detail"] = {
                        "layer": lv3,
                        "code": lc3.get("LCODE", lc3.get("l1_code", "")),
                        "landcover_label": _LANDCOVER_LABELS.get(code, "기타"),
                        "properties": lc3,
                    }
                    break

        if result:
            result["source"] = "환경공간정보 WMS (api.mcee.go.kr)"
            return result
        return None

    async def _wms_get_feature_info(
        self, client: httpx.AsyncClient, layer: str, bbox: str
    ) -> dict | None:
        """단일 WMS 레이어에 대해 GetFeatureInfo를 수행한다."""
        try:
            resp = await client.get(
                _LANDCOVER_WMS_URL,
                params={
                    "SERVICE": "WMS",
                    "VERSION": "1.1.1",
                    "REQUEST": "GetFeatureInfo",
                    "LAYERS": layer,
                    "QUERY_LAYERS": layer,
                    "SRS": "EPSG:3857",
                    "BBOX": bbox,
                    "WIDTH": 256,
                    "HEIGHT": 256,
                    "X": 128,
                    "Y": 128,
                    "INFO_FORMAT": "application/json",
                },
            )
            if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                info = resp.json()
                features = info.get("features", [])
                if features:
                    return features[0].get("properties", {})
        except Exception as e:
            logger.debug("WMS GetFeatureInfo %s failed: %s", layer, e)
        return None

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

