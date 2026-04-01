"""폐기물 발생현황 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 한국자원순환정보시스템 API (recycling-info.or.kr)
좌표 → 시도/시군구 → 폐기물 발생량/처리량 조회
"""

import asyncio
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

_WASTE_URL = "http://www.recycling-info.or.kr/sds/JsonApi.do"
# NTN001 = 전국 폐기물 발생 및 처리현황 (시도/시군구별)
_DEFAULT_PID = "NTN001"
_DEFAULT_YEAR = "2023"

# 시도명 → 폐기물 통계에서 사용하는 지역코드 매핑
_SIDO_MAP: dict[str, str] = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


async def _reverse_geocode_sido(lng: float, lat: float) -> str | None:
    """V-world 역지오코딩으로 시도명 추출."""
    vworld_key = settings.VWORLD_API_KEY
    if not vworld_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.vworld.kr/req/address",
                params={
                    "service": "address",
                    "request": "getAddress",
                    "version": "2.0",
                    "crs": "epsg:4326",
                    "point": f"{lng},{lat}",
                    "format": "json",
                    "type": "both",
                    "key": vworld_key,
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("response", {}).get("result", [])
            if results:
                addr = results[0].get("text", "")
                # 첫 번째 단어가 시도명
                parts = addr.split()
                if parts:
                    return parts[0]
    except Exception as e:
        logger.warning("V-world reverse geocode failed: %s", e)
    return None


class WasteDataConnector(BaseConnector):
    name = "waste_data"
    tier = DataTier.B
    description = "한국자원순환정보시스템 — 폐기물 발생량·처리량·재활용률"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 5000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.WASTE_API_KEY
        user_id = settings.WASTE_API_USERID
        if not api_key or not user_id:
            logger.info("WASTE_API_KEY or WASTE_API_USERID not set — fallback")
            return await self._fallback_to_cache()

        # 좌표 → 시도 변환
        sido_short = await _reverse_geocode_sido(lng, lat)
        region = _SIDO_MAP.get(sido_short or "", sido_short or "")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    _WASTE_URL,
                    params={
                        "PID": _DEFAULT_PID,
                        "YEAR": _DEFAULT_YEAR,
                        "USRID": user_id,
                        "KEY": api_key,
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Waste API HTTP %d — trying cache", resp.status_code
                    )
                    return await self._fallback_to_cache()

                raw = resp.json()

            # Rate limit 에러 처리
            result_code = raw.get("result", "")
            if result_code in ("E005", "E006"):
                logger.warning("Waste API rate limited (%s) — trying cache", result_code)
                await asyncio.sleep(1)
                return await self._fallback_to_cache()

            data = self._parse(raw, region)
            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
            return self._make_result(data)

        except Exception as e:
            logger.warning("Waste API failed: %s — trying cache", e)
            return await self._fallback_to_cache(str(e))

    def _parse(self, raw: dict, region: str) -> dict:
        """폐기물 통계 응답 파싱. 해당 시도 데이터만 추출."""
        # recycling-info API 응답 구조:
        # {"result": "S000", "dataHeader": [...], "data": [[...], ...]}
        header = raw.get("dataHeader", [])
        rows = raw.get("data", [])

        # dataHeader로 컬럼 인덱스 매핑
        col_map: dict[str, int] = {}
        for i, col in enumerate(header):
            name = col.get("colNm", col.get("name", f"col_{i}"))
            col_map[name] = i

        # 지역명을 포함하는 행 검색
        region_row = None
        region_name_idx = col_map.get("시도", col_map.get("지역", 0))

        for row in rows:
            if not isinstance(row, list) or len(row) <= region_name_idx:
                continue
            row_region = str(row[region_name_idx]).strip()
            if region and region in row_region:
                region_row = row
                break

        if region_row is None and rows:
            # 전국 합계 행 사용
            for row in rows:
                if isinstance(row, list) and len(row) > region_name_idx:
                    if "전국" in str(row[region_name_idx]) or "합계" in str(row[region_name_idx]):
                        region_row = row
                        break

        if region_row is None:
            return {
                "region": region or "알 수 없음",
                "waste_generation_ton_day": None,
                "waste_treatment_ton_day": None,
                "treatment_capacity_ratio": None,
                "recycled_ton": None,
                "incinerated_ton": None,
                "landfill_ton": None,
                "recycling_rate_pct": None,
                "facility_count": 0,
            }

        # 컬럼 매핑 (실제 API 응답의 컬럼명은 가변적)
        def _get_val(candidates: list[str]) -> float | None:
            for name in candidates:
                if name in col_map:
                    idx = col_map[name]
                    if idx < len(region_row):
                        return self._safe_float(region_row[idx])
            return None

        total = _get_val(["발생량", "총발생량", "발생량(톤/일)"]) or 0
        recycled = _get_val(["재활용", "재활용량", "재활용(톤/일)"])
        incinerated = _get_val(["소각", "소각량", "소각(톤/일)"])
        landfill = _get_val(["매립", "매립량", "매립(톤/일)"])

        treatment = sum(
            v for v in [recycled, incinerated, landfill] if v is not None
        )
        recycling_rate = (
            round(recycled / total * 100, 1) if recycled and total > 0 else None
        )

        return {
            "region": region or "알 수 없음",
            "waste_generation_ton_day": total if total > 0 else None,
            "waste_treatment_ton_day": treatment if treatment > 0 else None,
            "treatment_capacity_ratio": (
                round(treatment / total, 2) if total > 0 and treatment > 0 else None
            ),
            "recycled_ton": recycled,
            "incinerated_ton": incinerated,
            "landfill_ton": landfill,
            "recycling_rate_pct": recycling_rate,
            "facility_count": 1,
        }

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_result({
            "waste_generation_ton_day": None,
            "waste_treatment_ton_day": None,
            "treatment_capacity_ratio": None,
            "facility_count": 0,
        })
