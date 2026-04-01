"""에어코리아 대기질 커넥터 (B계층 — 불안정형+캐시).

데이터 소스: 에어코리아 OpenAPI (공공데이터포털)
1차: 좌표 → TM 변환 → getNearbyMsrstnList → 최근접 측정소명 획득
     → getMsrstnAcctoRltmMesureDnsty → 해당 측정소 실시간 데이터
2차 폴백: 좌표 → 시도명 → getCtprvnRltmMesureDnsty → 시도 전체 측정소
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

# ── 좌표 변환 (WGS84 → TM중부원점) ────────────────────────────────
_TM_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:2097", always_xy=True)

# ── 시도 경계 (폴백용) ─────────────────────────────────────────────
_SIDO_BOUNDS: list[tuple[str, float, float, float, float]] = [
    ("서울", 126.76, 127.18, 37.43, 37.70),
    ("세종", 126.85, 127.10, 36.48, 36.68),
    ("대전", 127.25, 127.50, 36.20, 36.48),
    ("인천", 126.37, 126.80, 37.35, 37.60),
    ("대구", 128.40, 128.77, 35.77, 36.00),
    ("부산", 128.85, 129.25, 35.05, 35.28),
    ("울산", 129.05, 129.45, 35.45, 35.70),
    ("광주", 126.75, 127.00, 35.08, 35.25),
    ("경기", 126.60, 127.90, 36.90, 38.30),
    ("강원", 127.00, 129.40, 37.00, 38.60),
    ("충북", 127.20, 128.10, 36.40, 37.15),
    ("충남", 125.90, 127.30, 36.00, 36.95),
    ("전북", 126.30, 127.90, 35.30, 36.15),
    ("전남", 126.00, 127.90, 34.00, 35.50),
    ("경북", 128.00, 129.60, 35.60, 37.10),
    ("경남", 127.50, 129.20, 34.60, 35.90),
    ("제주", 126.10, 126.98, 33.10, 33.60),
]

# 대기관리권역 시도 (대기환경보전법 시행령)
_AIR_MANAGEMENT_ZONES = {"서울", "인천", "경기", "대전", "세종", "충남", "충북"}

_AIRKOREA_BASE = "https://apis.data.go.kr/B552584"


def _wgs84_to_tm(lng: float, lat: float) -> tuple[float, float]:
    """WGS84 경위도를 TM중부원점(EPSG:2097) 좌표로 변환."""
    return _TM_TRANSFORMER.transform(lng, lat)


def _get_sido(lng: float, lat: float) -> str:
    """좌표로부터 시도명을 추정 (폴백용)."""
    for sido, lng_min, lng_max, lat_min, lat_max in _SIDO_BOUNDS:
        if lng_min <= lng <= lng_max and lat_min <= lat <= lat_max:
            return sido
    return "전국"


def _safe_float(v: Any) -> float | None:
    """에어코리아 응답값을 float로 안전 변환."""
    if v is None or v == "-" or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _khai_to_label(grade: str | None) -> str:
    """통합대기환경지수 등급 → 텍스트."""
    return {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우나쁨"}.get(
        str(grade), "알수없음"
    )


def _parse_realtime_item(item: dict, sido: str, distance_km: float | None = None) -> dict:
    """에어코리아 실시간 측정 항목을 룰 엔진 포맷으로 변환."""
    return {
        "station_name": item.get("stationName", ""),
        "data_time": item.get("dataTime", ""),
        "pm25_annual_avg": _safe_float(item.get("pm25Value")),
        "pm10_annual_avg": _safe_float(item.get("pm10Value")),
        "no2_annual_avg": _safe_float(item.get("no2Value")),
        "so2_annual_avg": _safe_float(item.get("so2Value")),
        "co_annual_avg": _safe_float(item.get("coValue")),
        "o3_annual_avg": _safe_float(item.get("o3Value")),
        "dust_source_distance_m": None,
        "regulated_zone": sido in _AIR_MANAGEMENT_ZONES,
        "air_quality_index": _khai_to_label(item.get("khaiGrade")),
        "odor_management_zone": None,
        "station_distance_km": distance_km,
    }


class AirQualityConnector(BaseConnector):
    name = "air_quality"
    tier = DataTier.B
    description = "에어코리아 — 대기오염물질 실시간 측정 데이터"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.AIRKOREA_API_KEY or settings.DATA_GO_KR_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        sido = _get_sido(lng, lat)

        # 1차: 근접측정소 API (좌표 → TM → 최근접 측정소 → 실시간 데이터)
        try:
            data = await self._fetch_by_nearby_station(api_key, lng, lat, sido)
            if data:
                self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
                return self._make_result(data)
        except Exception as e:
            logger.info("Nearby station API unavailable: %s - trying sido fallback", e)

        # 2차: 시도별 API (폴백)
        try:
            data = await self._fetch_by_sido(api_key, sido)
            if data:
                self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
                return self._make_result(data)
        except Exception as e:
            logger.warning("AirKorea sido API failed: %s - trying cache", e)

        return await self._fallback_to_cache(str(e) if "e" in dir() else "")

    async def _fetch_by_nearby_station(
        self, api_key: str, lng: float, lat: float, sido: str
    ) -> dict | None:
        """근접측정소 조회 → 해당 측정소 실시간 데이터."""
        tm_x, tm_y = _wgs84_to_tm(lng, lat)

        async with httpx.AsyncClient(timeout=8) as client:
            # Step 1: 근접 측정소 조회
            resp = await client.get(
                f"{_AIRKOREA_BASE}/MsrstnInfoInqireSvc/getNearbyMsrstnList",
                params={
                    "serviceKey": api_key,
                    "tmX": f"{tm_x:.6f}",
                    "tmY": f"{tm_y:.6f}",
                    "returnType": "json",
                    "ver": "1.1",
                },
            )
            if resp.status_code == 403:
                logger.info("getNearbyMsrstnList returned 403 (not authorized)")
                return None
            resp.raise_for_status()
            nearby = resp.json()

        items = nearby.get("response", {}).get("body", {}).get("items", [])
        if not items:
            return None

        station_name = items[0].get("stationName", "")
        distance_km = _safe_float(items[0].get("tm"))
        if not station_name:
            return None

        logger.info("Nearest station: %s (%.1f km)", station_name, distance_km or 0)

        # Step 2: 해당 측정소 실시간 데이터 조회
        async with httpx.AsyncClient(timeout=8) as client:
            resp2 = await client.get(
                f"{_AIRKOREA_BASE}/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty",
                params={
                    "serviceKey": api_key,
                    "stationName": station_name,
                    "dataTerm": "DAILY",
                    "returnType": "json",
                    "numOfRows": 1,
                    "pageNo": 1,
                    "ver": "1.0",
                },
            )
            resp2.raise_for_status()
            realtime = resp2.json()

        rt_items = realtime.get("response", {}).get("body", {}).get("items", [])
        if not rt_items:
            return None

        return _parse_realtime_item(rt_items[0], sido, distance_km)

    async def _fetch_by_sido(self, api_key: str, sido: str) -> dict | None:
        """시도별 실시간 측정 데이터 (폴백)."""
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{_AIRKOREA_BASE}/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
                params={
                    "serviceKey": api_key,
                    "sidoName": sido,
                    "returnType": "json",
                    "numOfRows": 200,
                    "pageNo": 1,
                    "ver": "1.0",
                },
            )
            resp.raise_for_status()
            body = resp.json()

        items = body.get("response", {}).get("body", {}).get("items", [])
        if not items:
            return None

        # 유효한 PM2.5 값이 있는 첫 측정소 선택
        best = items[0]
        for item in items:
            if _safe_float(item.get("pm25Value")) is not None:
                best = item
                break

        return _parse_realtime_item(best, sido)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

