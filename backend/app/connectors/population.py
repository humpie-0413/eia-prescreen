"""인구주거 커넥터 (B계층 — 로컬 CSV 기반).

데이터 소스:
  - 인구주거_조사_20231222.csv (18,614 rows, cp949) — 과거 EIA 프로젝트별 인구·가구·주택 조사
  - 인구주거_예측_20231222.csv (939 rows, cp949) — 사업 후 예측 인구
EIA 프로젝트 이력 데이터 — 집계 통계를 컨텍스트로 제공한다.
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

_DATA_DIR = Path("data/new/기후에너지환경부 국립환경과학원_환경영향평가  인구주거정보_20231222")
_SURVEY_CSV = _DATA_DIR / "인구주거_조사_20231222.csv"
_PREDICT_CSV = _DATA_DIR / "인구주거_예측_20231222.csv"


def _safe_float(val: str) -> Optional[float]:
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip().replace(",", ""))
    except ValueError:
        return None


def _safe_int(val: str) -> Optional[int]:
    f = _safe_float(val)
    return int(f) if f is not None else None


class PopulationConnector(BaseConnector):
    name = "population"
    tier = DataTier.B
    description = "환경영향평가 인구주거정보 (CSV, 18,614건 조사 + 939건 예측)"

    def __init__(self) -> None:
        self._summary: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._load_csv()

    def _load_csv(self) -> None:
        """조사·예측 CSV를 읽어 요약 통계를 사전 계산한다."""
        survey_stats = self._load_survey()
        predict_stats = self._load_prediction()

        if survey_stats is None and predict_stats is None:
            return

        self._summary = {
            "source": "환경영향평가 인구주거정보 (2023.12)",
            "survey": survey_stats,
            "prediction": predict_stats,
            "note": "과거 EIA 프로젝트별 인구·가구·주택 조사 및 예측 데이터 집계",
        }
        self._loaded = True

    def _load_survey(self) -> Optional[Dict[str, Any]]:
        """조사 CSV 로드."""
        if not _SURVEY_CSV.exists():
            logger.warning("Population survey CSV not found: %s", _SURVEY_CSV)
            return None

        try:
            total_rows = 0
            unique_projects: set = set()
            unique_regions: set = set()
            pop_values: List[int] = []
            household_values: List[int] = []
            house_values: List[int] = []
            supply_rates: List[float] = []

            with open(_SURVEY_CSV, encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                # 헤더에 영문 코드가 괄호 안에 있음
                for row in reader:
                    total_rows += 1
                    # DictReader가 첫 줄 헤더를 키로 사용
                    keys = list(row.keys())
                    # 사업코드 (첫 번째 컬럼)
                    bsns_cd = row.get(keys[0], "").strip()
                    if bsns_cd:
                        unique_projects.add(bsns_cd)
                    # 지역명 (두 번째 컬럼)
                    region = row.get(keys[1], "").strip()
                    if region:
                        unique_regions.add(region)
                    # 인구수_합계 (여섯 번째 컬럼, index 5)
                    pop = _safe_int(row.get(keys[5], "")) if len(keys) > 5 else None
                    if pop is not None and pop > 0:
                        pop_values.append(pop)
                    # 총 가구수 (일곱 번째 컬럼, index 6)
                    hh = _safe_int(row.get(keys[6], "")) if len(keys) > 6 else None
                    if hh is not None and hh > 0:
                        household_values.append(hh)
                    # 총 주택수 (여덟 번째 컬럼, index 7)
                    house = _safe_int(row.get(keys[7], "")) if len(keys) > 7 else None
                    if house is not None and house > 0:
                        house_values.append(house)
                    # 주택보급률 (아홉 번째 컬럼, index 8)
                    sr = _safe_float(row.get(keys[8], "")) if len(keys) > 8 else None
                    if sr is not None and 0 < sr <= 200:
                        supply_rates.append(sr)

            stats: Dict[str, Any] = {
                "total_records": total_rows,
                "unique_projects": len(unique_projects),
                "unique_regions": len(unique_regions),
            }
            if pop_values:
                stats["population"] = {
                    "count": len(pop_values),
                    "mean": round(sum(pop_values) / len(pop_values), 0),
                    "min": min(pop_values),
                    "max": max(pop_values),
                }
            if household_values:
                stats["households"] = {
                    "count": len(household_values),
                    "mean": round(sum(household_values) / len(household_values), 0),
                    "min": min(household_values),
                    "max": max(household_values),
                }
            if supply_rates:
                stats["housing_supply_rate"] = {
                    "count": len(supply_rates),
                    "mean_pct": round(sum(supply_rates) / len(supply_rates), 2),
                    "min_pct": round(min(supply_rates), 2),
                    "max_pct": round(max(supply_rates), 2),
                }

            logger.info("Population survey CSV loaded: %d rows, %d projects", total_rows, len(unique_projects))
            return stats

        except Exception as e:
            logger.error("Failed to load population survey CSV: %s", e)
            return None

    def _load_prediction(self) -> Optional[Dict[str, Any]]:
        """예측 CSV 로드."""
        if not _PREDICT_CSV.exists():
            logger.warning("Population prediction CSV not found: %s", _PREDICT_CSV)
            return None

        try:
            total_rows = 0
            unique_projects: set = set()

            with open(_PREDICT_CSV, encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_rows += 1
                    keys = list(row.keys())
                    bsns_cd = row.get(keys[0], "").strip()
                    if bsns_cd:
                        unique_projects.add(bsns_cd)

            stats = {
                "total_records": total_rows,
                "unique_projects": len(unique_projects),
            }
            logger.info("Population prediction CSV loaded: %d rows", total_rows)
            return stats

        except Exception as e:
            logger.error("Failed to load population prediction CSV: %s", e)
            return None

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if not self._loaded or self._summary is None:
            return self._make_empty_result("인구주거 CSV 데이터 미확보")

        freshness = DataFreshness(
            fetched_at=datetime.now(),
            snapshot_at=datetime(2023, 12, 22),
            fallback_used=False,
            freshness="cached",
        )
        return self._make_result(self._summary, ConnectorStatus.STABLE, freshness)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        """로컬 CSV 기반이므로 폴백 불필요 — 빈 결과 반환."""
        return self._make_empty_result(error or "No data available")
