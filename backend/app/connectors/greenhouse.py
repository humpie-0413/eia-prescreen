"""온실가스 커넥터 (C계층 — 로컬 CSV 기반).

데이터 소스: 기후에너지환경부 온실가스종합정보센터_국가 온실가스 인벤토리 배출량_20251229.csv
162 rows (분야별 카테고리), 컬럼=연도(1990~2023), utf-8-sig 인코딩.
국가 온실가스 인벤토리 집계 데이터 — 최신연도(2023) 분야별 배출량 요약을 제공한다.
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

_CSV_PATH = Path("data/new/기후에너지환경부 온실가스종합정보센터_국가 온실가스 인벤토리 배출량_20251229.csv")

# 관심 분야 (최상위 카테고리)
_KEY_SECTORS = [
    "총배출량",
    "순배출량",
    "에너지",
    "산업공정 및 제품사용",
    "농업",
    "LULUCF",
    "폐기물",
]


def _safe_float(val: str) -> Optional[float]:
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip().replace(",", ""))
    except ValueError:
        return None


class GreenhouseConnector(BaseConnector):
    name = "greenhouse"
    tier = DataTier.C
    description = "국가 온실가스 인벤토리 배출량 (CSV, 1990-2023)"

    def __init__(self) -> None:
        self._summary: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._load_csv()

    def _load_csv(self) -> None:
        """CSV를 읽어 요약 데이터를 사전 계산한다."""
        if not _CSV_PATH.exists():
            logger.warning("Greenhouse CSV not found: %s", _CSV_PATH)
            return

        try:
            rows: List[Dict[str, str]] = []
            with open(_CSV_PATH, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                for row in reader:
                    rows.append(row)

            total = len(rows)
            if total == 0:
                logger.warning("Greenhouse CSV is empty")
                return

            # 헤더에서 첫 번째 컬럼명 (분야 및 연도)과 연도 컬럼 추출
            sector_col = fieldnames[0] if fieldnames else ""
            year_cols = [c for c in fieldnames[1:] if c.strip().isdigit()]
            latest_year = max(year_cols) if year_cols else ""

            # 최신연도 분야별 배출량
            latest_by_sector: Dict[str, Optional[float]] = {}
            all_sectors: List[Dict[str, Any]] = []
            for row in rows:
                sector_name = row.get(sector_col, "").strip()
                if not sector_name:
                    continue
                latest_val = _safe_float(row.get(latest_year, "")) if latest_year else None
                all_sectors.append({
                    "sector": sector_name,
                    "value_kt_co2eq": latest_val,
                    "year": latest_year,
                })
                # 주요 분야: 정확 매칭 또는 시작 매칭 (하위 카테고리 제외)
                for key in _KEY_SECTORS:
                    # "LULUCF"는 정확 매칭, 나머지는 해당 키워드로 시작하는 최상위만
                    if sector_name == key or sector_name.startswith(key + "("):
                        latest_by_sector[sector_name] = latest_val
                        break

            # 총배출량 연도별 추이 (최근 10년)
            trend: Dict[str, Optional[float]] = {}
            for row in rows:
                sector_name = row.get(sector_col, "").strip()
                if "총배출량" in sector_name:
                    for yr in year_cols[-10:]:
                        trend[yr] = _safe_float(row.get(yr, ""))
                    break

            self._summary = {
                "source": "국가 온실가스 인벤토리 배출량 (2025.12 공표)",
                "total_categories": total,
                "latest_year": latest_year,
                "key_sectors": latest_by_sector,
                "total_emission_trend_10yr": trend,
                "all_sectors_count": len(all_sectors),
                "unit": "kt CO2-eq",
                "note": "국가 온실가스 인벤토리 집계 데이터 (전국 단위, 분야별 배출량)",
            }
            self._loaded = True
            logger.info("Greenhouse CSV loaded: %d categories", total)

        except Exception as e:
            logger.error("Failed to load greenhouse CSV: %s", e)

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if not self._loaded or self._summary is None:
            return self._make_empty_result("온실가스 CSV 데이터 미확보")

        freshness = DataFreshness(
            fetched_at=datetime.now(),
            snapshot_at=datetime(2025, 12, 29),
            fallback_used=False,
            freshness="cached",
        )
        return self._make_result(self._summary, ConnectorStatus.STABLE, freshness)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        """로컬 CSV 기반이므로 폴백 불필요 — 빈 결과 반환."""
        return self._make_empty_result(error or "No data available")
