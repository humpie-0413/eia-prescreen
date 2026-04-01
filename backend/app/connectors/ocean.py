"""해양환경(조위·수온·조류) 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 국립해양조사원 API (KHOA)
좌표 기반 가장 가까운 관측소 → 조위·수온·조류 조회
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
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

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "static"
_STATIONS: list[dict] | None = None
_MAX_DISTANCE_KM = 50

_TIDE_URL = (
    "http://www.khoa.go.kr/api/oceangrid/tideObsPreTab/search.do"
)
_BUOY_URL = (
    "http://www.khoa.go.kr/api/oceangrid/buObsRecent/search.do"
)


def _load_stations() -> list[dict]:
    global _STATIONS
    if _STATIONS is None:
        path = _STATIC_DIR / "khoa_stations.json"
        with open(path, encoding="utf-8") as f:
            _STATIONS = json.load(f)
    return _STATIONS


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearest_station(lng: float, lat: float) -> tuple[dict | None, float]:
    stations = _load_stations()
    best = None
    best_dist = float("inf")
    for st in stations:
        dist = _haversine_km(lat, lng, st["lat"], st["lng"])
        if dist < best_dist:
            best_dist = dist
            best = st
    if best_dist > _MAX_DISTANCE_KM:
        return None, best_dist
    return best, best_dist


class OceanConnector(BaseConnector):
    name = "ocean"
    tier = DataTier.B
    description = "국립해양조사원 — 조위·수온·조류 관측"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 5000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.KHOA_API_KEY
        if not api_key:
            # Fallback to DATA_GO_KR key if KHOA key not set
            api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        station, dist_km = _find_nearest_station(lng, lat)
        if station is None:
            logger.info("No ocean station within %dkm", _MAX_DISTANCE_KM)
            return self._make_empty_result(
                f"50km 이내 조위관측소 없음 (최근접 {dist_km:.0f}km)"
            )

        try:
            today = datetime.now().strftime("%Y%m%d")
            tide_data = await self._fetch_tide(api_key, station["obs_code"], today)
            data = self._build_result(station, dist_km, tide_data)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("KHOA API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    async def _fetch_tide(
        self, api_key: str, obs_code: str, date: str
    ) -> list[dict]:
        """조위관측소 실측 조위 조회."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    _TIDE_URL,
                    params={
                        "ServiceKey": api_key,
                        "ObsCode": obs_code,
                        "Date": date,
                        "ResultType": "json",
                    },
                )
                if resp.status_code != 200:
                    logger.warning("KHOA tide API HTTP %d", resp.status_code)
                    return []

                raw = resp.json()
                result = raw.get("result", {})
                data = result.get("data", [])
                if isinstance(data, dict):
                    data = [data]
                return data
        except Exception as e:
            logger.warning("KHOA tide fetch error: %s", e)
            return []

    def _build_result(
        self, station: dict, dist_km: float, tide_data: list[dict]
    ) -> dict:
        """관측 데이터를 정규화된 형태로 변환."""
        tide_records = []
        for item in tide_data:
            tide_records.append({
                "datetime": item.get("record_time", item.get("obs_time", "")),
                "tide_level_cm": self._safe_float(
                    item.get("tide_level", item.get("obs_level"))
                ),
            })

        latest_tide = None
        if tide_records:
            latest_tide = tide_records[-1].get("tide_level_cm")

        return {
            "station_name": station["name"],
            "obs_code": station["obs_code"],
            "distance_km": round(dist_km, 1),
            "tide_records": tide_records[-24:],
            "tide_record_count": len(tide_records),
            "tide_level": latest_tide,
            "water_temp_c": None,
            "current_dir": None,
            "current_speed": None,
            "wave_height_m": None,
            "depth": None,
            "stations": [{"station_name": station["name"], "tide_level": latest_tide}],
            "station_count": 1,
            "tidal_current": None,
            "tidal_impact_review_needed": dist_km < 10,
            "depth_change_expected": False,
        }

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
        return self._make_result({
            "stations": [],
            "station_count": 0,
            "depth": None,
            "tidal_current": None,
            "tide_level": None,
            "station_name": None,
            "tidal_impact_review_needed": False,
            "depth_change_expected": False,
        })
