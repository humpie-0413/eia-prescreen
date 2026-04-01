"""수리·수문 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: K-water 수문 운영 정보 (apis.data.go.kr/B500001)
좌표 기반 가장 가까운 댐/보 → 시간 수위·유량 조회
"""

import json
import logging
import math
from datetime import datetime, timedelta
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
_DAM_CODES: list[dict] | None = None
_MAX_DISTANCE_KM = 50


def _load_dam_codes() -> list[dict]:
    global _DAM_CODES
    if _DAM_CODES is None:
        path = _STATIC_DIR / "kwater_dam_codes.json"
        with open(path, encoding="utf-8") as f:
            _DAM_CODES = json.load(f)
    return _DAM_CODES


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 하버사인 거리 (km)."""
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


def _find_nearest_dam(lng: float, lat: float) -> tuple[dict | None, float]:
    """좌표에서 가장 가까운 댐을 찾는다. (50km 이내)"""
    dams = _load_dam_codes()
    best = None
    best_dist = float("inf")
    for dam in dams:
        dist = _haversine_km(lat, lng, dam["lat"], dam["lng"])
        if dist < best_dist:
            best_dist = dist
            best = dam
    if best_dist > _MAX_DISTANCE_KM:
        return None, best_dist
    return best, best_dist


class HydrologyConnector(BaseConnector):
    name = "hydrology"
    tier = DataTier.B
    description = "K-water 수문 운영 정보 — 댐 수위·유입량·방류량·저수율"

    _BASE_URL = "http://apis.data.go.kr/B500001/dam/sluicePresentCondition/hourlist"

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

        dam, dist_km = _find_nearest_dam(lng, lat)
        if dam is None:
            logger.info("No dam within %dkm — returning empty", _MAX_DISTANCE_KM)
            return self._make_empty_result(
                f"50km 이내 댐 없음 (최근접 {dist_km:.0f}km)"
            )

        try:
            now = datetime.now()
            stdt = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            eddt = now.strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self._BASE_URL,
                    params={
                        "serviceKey": api_key,
                        "damcode": dam["damcode"],
                        "stdt": stdt,
                        "eddt": eddt,
                        "pageNo": "1",
                        "numOfRows": "24",
                        "_type": "json",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "K-water API HTTP %d — trying cache", resp.status_code
                    )
                    return await self._fallback_to_cache()

                raw = resp.json()

            data = self._parse(raw, dam, dist_km)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("K-water API failed: %s — trying cache", e)
            return await self._fallback_to_cache()

    def _parse(self, raw: dict, dam: dict, dist_km: float) -> dict:
        """K-water 응답에서 수문 관측 정보 추출."""
        # API 응답 구조: {"response":{"header":...,"body":{"items":[...]}}}
        body = raw.get("response", raw).get("body", raw)
        items = body.get("items", body.get("list", body.get("data", [])))
        if isinstance(items, dict):
            items = items.get("item", [items])
        if isinstance(items, dict):
            items = [items]

        records = []
        for item in items:
            records.append({
                "datetime": item.get("ymdhm", item.get("datetime", "")),
                "water_level_m": self._safe_float(
                    item.get("rwl", item.get("wl"))
                ),
                "rainfall_mm": self._safe_float(
                    item.get("rf", item.get("rainfall"))
                ),
                "inflow_m3s": self._safe_float(
                    item.get("inf", item.get("inflow"))
                ),
                "discharge_m3s": self._safe_float(
                    item.get("totdcwtrqty", item.get("sluiceDis", item.get("discharge")))
                ),
                "storage_mcm": self._safe_float(
                    item.get("rsqty", item.get("storage"))
                ),
                "storage_rate_pct": self._safe_float(
                    item.get("rspct", item.get("storage_rate"))
                ),
            })

        latest = records[0] if records else {}

        return {
            "dam_name": dam["name"],
            "damcode": dam["damcode"],
            "distance_km": round(dist_km, 1),
            "records": records[:24],
            "record_count": len(records),
            "water_level": latest.get("water_level_m"),
            "flow_rate": latest.get("inflow_m3s"),
            "storage_rate_pct": latest.get("storage_rate_pct"),
            "river_name": dam["name"].replace("댐", ""),
            "stations": [{"station_name": dam["name"]}],
            "station_count": 1,
            "flood_risk_zone": (latest.get("storage_rate_pct") or 0) > 90,
            "low_flow_section": (latest.get("storage_rate_pct") or 100) < 20,
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
            "dam_name": None,
            "stations": [],
            "station_count": 0,
            "flood_risk_zone": False,
            "low_flow_section": False,
            "river_name": None,
            "water_level": None,
            "flow_rate": None,
        })
