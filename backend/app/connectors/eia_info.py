"""환경영향평가 정보 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스:
  1. 좌표 기반 주변 환평 사업 검색 (getBsnsPlaceLnMyeonInfoInqire)
     - gubun 1~15: 사업지, 멸종위기종, 대기/수질/토양 측정지점 등
     - centerX=위도, centerY=경도 (API 좌표 규약: X=lat, Y=lon)
  2. 사전/전략/소규모 상세정보 (getBsnsStrtgySmallScaleDscssBsnsDetailInfoInqire)
     - perCd 기반 조회: 사업명, 협의기관, 담당자 등
  3. 협의진행 현황 (getBsnsStrtgySmallScaleDscssBsnsDetailIngInfoInqire)
     - perCd 기반 조회: 접수일, 협의단계 이력
"""

import logging
import math
import re
import xml.etree.ElementTree as ET
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

# ── API URLs ──

_SPATIAL_URL = (
    "https://apis.data.go.kr/1480523/"
    "EnvrnAffcEvlBsnsInfoInqireService/"
    "getBsnsPlaceLnMyeonInfoInqire"
)

_CONSLT_SVC_BASE = (
    "https://apis.data.go.kr/1480523/"
    "BeffatStrtgySmallScaleDscssSttusInfoInqireService"
)
_DETAIL_URL = f"{_CONSLT_SVC_BASE}/getBsnsStrtgySmallScaleDscssBsnsDetailInfoInqire"
_ING_URL = f"{_CONSLT_SVC_BASE}/getBsnsStrtgySmallScaleDscssBsnsDetailIngInfoInqire"

# ── Gubun (공간 데이터 유형) ──

GUBUN_LABELS: dict[int, str] = {
    1: "사업지_선",
    2: "사업지_면",
    3: "멸종위기동물_점",
    4: "멸종위기동물_선",
    5: "멸종위기동물_면",
    6: "멸종위기식물_점",
    7: "멸종위기식물_면",
    8: "대기질_점",
    9: "해양저질",
    10: "해양수질",
    11: "지표수질",
    12: "지하수질",
    13: "토양질",
    14: "멸종위기동물_선2",
    15: "진동",
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 WGS84 좌표 간 거리(km)를 계산한다."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_xml_items(xml_text: str) -> list[dict[str, str]]:
    """XML 응답에서 item 목록을 파싱한다."""
    items: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
        for item_el in root.iter("item"):
            row: dict[str, str] = {}
            for child in item_el:
                if child.text:
                    row[child.tag] = child.text
            if row:
                items.append(row)
    except ET.ParseError:
        # regex fallback
        for item_xml in re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL):
            fields = dict(re.findall(r"<(\w+)>([^<]+)</\w+>", item_xml))
            if fields:
                items.append(fields)
    return items


class EiaInfoConnector(BaseConnector):
    name = "eia_info"
    tier = DataTier.B
    description = "환경영향평가 정보 — 주변 환평 사업 검색·멸종위기종·환경 측정지점"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 5000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        try:
            data = await self._fetch_spatial_data(api_key, lng, lat, buffer_m)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)
        except Exception as e:
            logger.warning("EIA Info API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    async def _fetch_spatial_data(
        self,
        api_key: str,
        lng: float,
        lat: float,
        buffer_m: float,
    ) -> dict[str, Any]:
        """좌표 기반으로 주변 환평 데이터를 수집한다 (6개 API 병렬 호출)."""
        import asyncio

        radius_km = buffer_m / 1000

        async with httpx.AsyncClient(timeout=15) as client:
            # 6개 gubun을 병렬 호출 (기존 순차 호출 → 병렬)
            (
                projects,
                endangered_animals,
                endangered_plants,
                air_points,
                water_points,
                soil_points,
            ) = await asyncio.gather(
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=2, num_rows=100),
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=3, num_rows=50),
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=6, num_rows=50),
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=8, num_rows=30),
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=11, num_rows=30),
                self._fetch_spatial_gubun(client, api_key, lat, lng, gubun=13, num_rows=30),
            )

            nearby_projects = self._filter_by_distance(projects, lat, lng, radius_km)
            nearby_animals = self._filter_by_distance(endangered_animals, lat, lng, radius_km)
            nearby_plants = self._filter_by_distance(endangered_plants, lat, lng, radius_km)
            nearby_air = self._filter_by_distance(air_points, lat, lng, radius_km)
            nearby_water = self._filter_by_distance(water_points, lat, lng, radius_km)
            nearby_soil = self._filter_by_distance(soil_points, lat, lng, radius_km)

        return {
            "nearby_eia_count": len(nearby_projects),
            "nearby_eia_projects": [
                {
                    "name": p.get("name", ""),
                    "num": p.get("num", ""),
                    "distance_km": round(p["_dist_km"], 1),
                    "centerx": p.get("centerx", ""),
                    "centery": p.get("centery", ""),
                }
                for p in nearby_projects[:10]
            ],
            "endangered_species_points": len(nearby_animals) + len(nearby_plants),
            "endangered_animals": [
                {"name": a.get("name", ""), "distance_km": round(a["_dist_km"], 1)}
                for a in nearby_animals[:10]
            ],
            "endangered_plants": [
                {"name": p.get("name", ""), "distance_km": round(p["_dist_km"], 1)}
                for p in nearby_plants[:10]
            ],
            "air_quality_points": len(nearby_air),
            "water_quality_points": len(nearby_water),
            "soil_quality_points": len(nearby_soil),
            "search_radius_km": radius_km,
            "total_eia_db_count": len(projects),
        }

    async def _fetch_spatial_gubun(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        lat: float,
        lng: float,
        gubun: int,
        num_rows: int = 100,
    ) -> list[dict[str, str]]:
        """좌표 기반 공간 검색 API 호출 (단일 gubun)."""
        try:
            resp = await client.get(
                _SPATIAL_URL,
                params={
                    "serviceKey": api_key,
                    "gubun": gubun,
                    "centerX": lat,   # API 규약: X=위도
                    "centerY": lng,   # API 규약: Y=경도
                    "distance": 5000,
                    "numOfRows": num_rows,
                    "pageNo": 1,
                },
            )
            resp.raise_for_status()
            return _parse_xml_items(resp.text)
        except Exception as e:
            logger.warning("Spatial API gubun=%d failed: %s", gubun, e)
            return []

    def _filter_by_distance(
        self,
        items: list[dict[str, str]],
        center_lat: float,
        center_lng: float,
        radius_km: float,
    ) -> list[dict]:
        """haversine 거리로 반경 내 항목만 필터링한다."""
        filtered: list[dict] = []
        for item in items:
            try:
                item_lon = float(item.get("centerx", 0))
                item_lat = float(item.get("centery", 0))
                if item_lon == 0 or item_lat == 0:
                    continue
                dist_km = _haversine_km(center_lat, center_lng, item_lat, item_lon)
                if dist_km <= radius_km:
                    enriched = {**item, "_dist_km": dist_km}
                    filtered.append(enriched)
            except (ValueError, TypeError):
                continue
        filtered.sort(key=lambda x: x["_dist_km"])
        return filtered

    async def fetch_detail(self, per_cd: str) -> dict[str, Any] | None:
        """perCd로 사업 상세정보를 조회한다."""
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    _DETAIL_URL,
                    params={"serviceKey": api_key, "perCd": per_cd},
                )
                resp.raise_for_status()
                items = _parse_xml_items(resp.text)
                return items[0] if items else None
        except Exception as e:
            logger.warning("Detail API failed for %s: %s", per_cd, e)
            return None

    async def fetch_consultation_progress(self, per_cd: str) -> list[dict[str, str]]:
        """perCd로 협의진행 이력을 조회한다."""
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    _ING_URL,
                    params={"serviceKey": api_key, "perCd": per_cd},
                )
                resp.raise_for_status()
                return _parse_xml_items(resp.text)
        except Exception as e:
            logger.warning("Consultation progress API failed for %s: %s", per_cd, e)
            return []

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

