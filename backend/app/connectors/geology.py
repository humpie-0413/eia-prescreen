"""지형지질 커넥터 (B계층 — 로컬 CSV 기반).

데이터 소스: 기후에너지환경부 국립환경과학원_환경영향평가 지형지질정보_20241216/
  - 지형지질_개요_20230118.csv (2,060 rows, cp949) — 주요 파일
  - 지형지질_경사_20241216.csv, 지형지질_표고_20241216.csv 등 보조 파일
EIA 프로젝트별 지형지질 조사 이력 데이터 — 집계 통계를 컨텍스트로 제공한다.
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

_DATA_DIR = Path("data/new/기후에너지환경부 국립환경과학원_환경영향평가  지형지질정보_20241216")
_OVERVIEW_CSV = _DATA_DIR / "지형지질_개요_20230118.csv"
_SLOPE_CSV = _DATA_DIR / "지형지질_경사_20241216.csv"
_ELEVATION_CSV = _DATA_DIR / "지형지질_표고_20241216.csv"


def _safe_float(val: str) -> Optional[float]:
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip().replace(",", ""))
    except ValueError:
        return None


def _compute_stats(values: List[float]) -> Dict[str, Any]:
    """기본 통계(count, mean, min, max)를 계산한다."""
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


class GeologyConnector(BaseConnector):
    name = "geology"
    tier = DataTier.B
    description = "환경영향평가 지형지질정보 (CSV, 2,060건 개요 + 경사/표고)"

    def __init__(self) -> None:
        self._summary: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._load_csv()

    def _load_csv(self) -> None:
        """개요·경사·표고 CSV를 읽어 요약 통계를 사전 계산한다."""
        overview = self._load_overview()
        slope = self._load_slope()
        elevation = self._load_elevation()

        if overview is None and slope is None and elevation is None:
            return

        self._summary = {
            "source": "환경영향평가 지형지질정보 (2024.12)",
            "overview": overview,
            "slope": slope,
            "elevation": elevation,
            "note": "과거 EIA 프로젝트별 지형지질 조사 데이터 집계 (절토/성토량, 경사, 표고 등)",
        }
        self._loaded = True

    def _load_overview(self) -> Optional[Dict[str, Any]]:
        """개요 CSV 로드 — 절토량, 성토량, 최대깎기고, 지형변화지수 등."""
        if not _OVERVIEW_CSV.exists():
            logger.warning("Geology overview CSV not found: %s", _OVERVIEW_CSV)
            return None

        try:
            total_rows = 0
            unique_projects: set = set()
            cut_volumes: List[float] = []       # 절토량
            fill_volumes: List[float] = []      # 성토량
            max_cut_heights: List[float] = []   # 최대깎기고
            max_fill_heights: List[float] = []  # 최대쌓기고
            topo_indices: List[float] = []      # 지형변화지수

            with open(_OVERVIEW_CSV, encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                keys_list: List[str] = []
                for row in reader:
                    if not keys_list:
                        keys_list = list(row.keys())
                    total_rows += 1

                    bsns_cd = row.get(keys_list[0], "").strip()
                    if bsns_cd:
                        unique_projects.add(bsns_cd)

                    # 절토량 (index 1)
                    v = _safe_float(row.get(keys_list[1], "")) if len(keys_list) > 1 else None
                    if v is not None:
                        cut_volumes.append(v)
                    # 성토량 (index 2)
                    v = _safe_float(row.get(keys_list[2], "")) if len(keys_list) > 2 else None
                    if v is not None:
                        fill_volumes.append(v)
                    # 최대깎기고 (index 3)
                    v = _safe_float(row.get(keys_list[3], "")) if len(keys_list) > 3 else None
                    if v is not None:
                        max_cut_heights.append(v)
                    # 최대쌓기고 (index 5)
                    v = _safe_float(row.get(keys_list[5], "")) if len(keys_list) > 5 else None
                    if v is not None:
                        max_fill_heights.append(v)
                    # 지형변화지수 (index 8)
                    v = _safe_float(row.get(keys_list[8], "")) if len(keys_list) > 8 else None
                    if v is not None:
                        topo_indices.append(v)

            stats = {
                "total_records": total_rows,
                "unique_projects": len(unique_projects),
                "cut_volume_m3": _compute_stats(cut_volumes),
                "fill_volume_m3": _compute_stats(fill_volumes),
                "max_cut_height_m": _compute_stats(max_cut_heights),
                "max_fill_height_m": _compute_stats(max_fill_heights),
                "topographic_change_index": _compute_stats(topo_indices),
            }
            logger.info("Geology overview CSV loaded: %d rows, %d projects", total_rows, len(unique_projects))
            return stats

        except Exception as e:
            logger.error("Failed to load geology overview CSV: %s", e)
            return None

    def _load_slope(self) -> Optional[Dict[str, Any]]:
        """경사 CSV 로드 — 경사 등급별 면적/비율."""
        if not _SLOPE_CSV.exists():
            logger.warning("Geology slope CSV not found: %s", _SLOPE_CSV)
            return None

        try:
            total_rows = 0
            unique_projects: set = set()
            grade_counts: Dict[str, int] = {}

            with open(_SLOPE_CSV, encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                keys_list: List[str] = []
                for row in reader:
                    if not keys_list:
                        keys_list = list(row.keys())
                    total_rows += 1
                    bsns_cd = row.get(keys_list[0], "").strip()
                    if bsns_cd:
                        unique_projects.add(bsns_cd)
                    # 경사 등급 (index 1)
                    grade = row.get(keys_list[1], "").strip() if len(keys_list) > 1 else ""
                    if grade:
                        grade_counts[grade] = grade_counts.get(grade, 0) + 1

            stats = {
                "total_records": total_rows,
                "unique_projects": len(unique_projects),
                "grade_distribution": grade_counts,
            }
            logger.info("Geology slope CSV loaded: %d rows", total_rows)
            return stats

        except Exception as e:
            logger.error("Failed to load geology slope CSV: %s", e)
            return None

    def _load_elevation(self) -> Optional[Dict[str, Any]]:
        """표고 CSV 로드 — 표고 등급별 면적/비율."""
        if not _ELEVATION_CSV.exists():
            logger.warning("Geology elevation CSV not found: %s", _ELEVATION_CSV)
            return None

        try:
            total_rows = 0
            unique_projects: set = set()
            grade_counts: Dict[str, int] = {}

            with open(_ELEVATION_CSV, encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                keys_list: List[str] = []
                for row in reader:
                    if not keys_list:
                        keys_list = list(row.keys())
                    total_rows += 1
                    bsns_cd = row.get(keys_list[0], "").strip()
                    if bsns_cd:
                        unique_projects.add(bsns_cd)
                    # 표고 등급 (index 1)
                    grade = row.get(keys_list[1], "").strip() if len(keys_list) > 1 else ""
                    if grade:
                        grade_counts[grade] = grade_counts.get(grade, 0) + 1

            stats = {
                "total_records": total_rows,
                "unique_projects": len(unique_projects),
                "grade_distribution": grade_counts,
            }
            logger.info("Geology elevation CSV loaded: %d rows", total_rows)
            return stats

        except Exception as e:
            logger.error("Failed to load geology elevation CSV: %s", e)
            return None

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if not self._loaded or self._summary is None:
            return self._make_empty_result("지형지질 CSV 데이터 미확보")

        freshness = DataFreshness(
            fetched_at=datetime.now(),
            snapshot_at=datetime(2024, 12, 16),
            fallback_used=False,
            freshness="cached",
        )
        return self._make_result(self._summary, ConnectorStatus.STABLE, freshness)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        """로컬 CSV 기반이므로 폴백 불필요 — 빈 결과 반환."""
        return self._make_empty_result(error or "No data available")
