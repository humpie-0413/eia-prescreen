"""소음진동 커넥터 (B계층 — 로컬 CSV 기반).

데이터 소스: 한국환경공단_소음진동측정망 운영정보_20241231.csv
144,927 rows, utf-8-sig 인코딩.
도시별 소음도 측정 데이터 — 도시별 평균 소음도 및 전국 통계를 제공한다.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataFreshness,
    DataTier,
)

logger = logging.getLogger(__name__)

_CSV_PATH = Path("data/new/한국환경공단_소음진동측정망 운영정보_20241231.csv")


def _safe_float(val: str) -> Optional[float]:
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


class NoiseConnector(BaseConnector):
    name = "noise"
    tier = DataTier.B
    description = "소음진동측정망 운영정보 (CSV, 전국 144,927건)"

    def __init__(self) -> None:
        self._city_stats: Dict[str, Dict[str, Any]] = {}
        self._national_stats: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._load_csv()

    def _load_csv(self) -> None:
        """CSV를 읽어 도시별/전국 소음도 통계를 사전 계산한다."""
        if not _CSV_PATH.exists():
            logger.warning("Noise CSV not found: %s", _CSV_PATH)
            return

        try:
            # 도시별 소음도 수집
            city_values: Dict[str, List[float]] = {}
            all_values: List[float] = []
            zone_counts: Dict[str, int] = {}
            total_rows = 0

            with open(_CSV_PATH, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_rows += 1
                    city = row.get("도시", "").strip()
                    noise = _safe_float(row.get("소음도", ""))
                    zone = row.get("용도구분", "").strip()

                    if noise is not None:
                        all_values.append(noise)
                        if city:
                            if city not in city_values:
                                city_values[city] = []
                            city_values[city].append(noise)

                    if zone:
                        zone_counts[zone] = zone_counts.get(zone, 0) + 1

            if total_rows == 0:
                logger.warning("Noise CSV is empty")
                return

            # 도시별 평균/최소/최대 계산
            for city, values in city_values.items():
                self._city_stats[city] = {
                    "count": len(values),
                    "mean_db": round(sum(values) / len(values), 2),
                    "min_db": round(min(values), 2),
                    "max_db": round(max(values), 2),
                }

            # 전국 통계
            self._national_stats = {
                "source": "소음진동측정망 운영정보 (2024)",
                "total_records": total_rows,
                "total_cities": len(city_values),
                "national_mean_db": round(sum(all_values) / len(all_values), 2) if all_values else None,
                "national_min_db": round(min(all_values), 2) if all_values else None,
                "national_max_db": round(max(all_values), 2) if all_values else None,
                "zone_counts": zone_counts,
                "data_year": "2024",
            }
            self._loaded = True
            logger.info("Noise CSV loaded: %d rows, %d cities", total_rows, len(city_values))

        except Exception as e:
            logger.error("Failed to load noise CSV: %s", e)

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if not self._loaded or self._national_stats is None:
            return self._make_empty_result("소음 CSV 데이터 미확보")

        # 도시명이 kwargs로 전달되면 해당 도시 필터링
        city_name = kwargs.get("city", "")
        matched_city: Optional[Dict[str, Any]] = None
        if city_name:
            # 부분 매칭 시도
            for city_key, stats in self._city_stats.items():
                if city_name in city_key or city_key in city_name:
                    matched_city = {"city": city_key, **stats}
                    break

        data = {
            **self._national_stats,
            "city_stats": self._city_stats,
            "matched_city": matched_city,
            "note": "전국 소음진동측정망 데이터 (도시별 평균 소음도 포함)",
        }

        freshness = DataFreshness(
            fetched_at=datetime.now(),
            snapshot_at=datetime(2024, 12, 31),
            fallback_used=False,
            freshness="cached",
        )
        return self._make_result(data, ConnectorStatus.STABLE, freshness)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        """로컬 CSV 기반이므로 폴백 불필요 — 빈 결과 반환."""
        return self._make_empty_result(error or "No data available")
