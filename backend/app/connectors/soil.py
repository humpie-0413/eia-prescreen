"""토양 커넥터 (B계층 — 로컬 CSV 기반).

데이터 소스: 기후에너지환경부 국립환경과학원_토양오염실태조사 결과_20241231.csv
2,949 rows, cp949 인코딩.
좌표 없는 전국 토양오염 실태조사 데이터 — 요약 통계를 제공한다.
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

# 주요 중금속 오염물질 컬럼 (CSV 헤더 기준)
_POLLUTANT_COLS = [
    "카드뮴(mg_kg)",
    "구리(mg_kg)",
    "비소(mg_kg)",
    "니켈(mg_kg)",
    "납(mg_kg)",
    "6가크롬(mg_kg)",
    "아연(mg_kg)",
    "수은(mg_kg)",
    "불소(mg_kg)",
]

_CSV_PATH = Path("data/new/기후에너지환경부 국립환경과학원_토양오염실태조사 결과_20241231.csv")


def _safe_float(val: str) -> Optional[float]:
    """빈 문자열이나 파싱 불가 값은 None으로 반환."""
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


class SoilConnector(BaseConnector):
    name = "soil"
    tier = DataTier.B
    description = "토양오염실태조사 결과 (CSV, 전국 2,949건)"

    def __init__(self) -> None:
        self._summary: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._load_csv()

    def _load_csv(self) -> None:
        """CSV를 읽어 요약 통계를 사전 계산한다.

        cp949 인코딩의 일부 한글 문자가 UTF-8 소스 리터럴과 다르게 디코딩될 수 있으므로,
        컬럼 접근 시 헤더 인덱스 기반 매핑을 우선 사용한다.
        """
        if not _CSV_PATH.exists():
            logger.warning("Soil CSV not found: %s", _CSV_PATH)
            return

        try:
            # 인덱스 기반 매핑 (cp949 디코딩 불일치 방지)
            # 0:년도, 1:지점명칭, 2:목적, 3:지목, 4:지역, 5:면적,
            # 6:시료깊이, 7:카드뮴, 8:구리, 9:비소, 10:니켈, 11:납,
            # 12:6가크롬, 13:아연, 14:수은, 15:불소, 16:유기인,
            # 17:PCBs, 18:시안, 19:페놀, 20:벤젠, 21:톨루엔,
            # 22:에틸벤젠, 23:크실렌, 24:TPH, 25:TCE, 26:PCE,
            # 27:벤조피렌, 28:12디클로로에탄, 29:다이옥신, 30:토양산도(pH)
            _POLLUTANT_INDICES = {
                "cadmium_mg_kg": 7,
                "copper_mg_kg": 8,
                "arsenic_mg_kg": 9,
                "nickel_mg_kg": 10,
                "lead_mg_kg": 11,
                "chromium6_mg_kg": 12,
                "zinc_mg_kg": 13,
                "mercury_mg_kg": 14,
                "fluorine_mg_kg": 15,
            }
            _IDX_REGION = 4
            _IDX_PURPOSE = 2
            _IDX_PH = 30

            all_rows: List[List[str]] = []
            with open(_CSV_PATH, encoding="cp949", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader)  # skip header row
                for row in reader:
                    all_rows.append(row)

            total = len(all_rows)
            if total == 0:
                logger.warning("Soil CSV is empty")
                return

            # 지역별 건수
            region_counts: Dict[str, int] = {}
            for row in all_rows:
                region = row[_IDX_REGION].strip() if len(row) > _IDX_REGION else ""
                if region:
                    region_counts[region] = region_counts.get(region, 0) + 1

            # 목적별 건수
            purpose_counts: Dict[str, int] = {}
            for row in all_rows:
                purpose = row[_IDX_PURPOSE].strip() if len(row) > _IDX_PURPOSE else ""
                if purpose:
                    purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1

            # 주요 오염물질 평균
            pollutant_stats: Dict[str, Dict[str, Any]] = {}
            for label, idx in _POLLUTANT_INDICES.items():
                values = []
                for row in all_rows:
                    v = _safe_float(row[idx]) if len(row) > idx else None
                    if v is not None:
                        values.append(v)
                if values:
                    pollutant_stats[label] = {
                        "count": len(values),
                        "mean": round(sum(values) / len(values), 4),
                        "min": round(min(values), 4),
                        "max": round(max(values), 4),
                    }

            # pH 통계
            ph_values = []
            for row in all_rows:
                v = _safe_float(row[_IDX_PH]) if len(row) > _IDX_PH else None
                if v is not None:
                    ph_values.append(v)
            ph_stats = None
            if ph_values:
                ph_stats = {
                    "count": len(ph_values),
                    "mean": round(sum(ph_values) / len(ph_values), 2),
                    "min": round(min(ph_values), 2),
                    "max": round(max(ph_values), 2),
                }

            self._summary = {
                "source": "토양오염실태조사 결과 (2024)",
                "total_records": total,
                "region_counts": region_counts,
                "purpose_counts": purpose_counts,
                "pollutant_averages": pollutant_stats,
                "ph_stats": ph_stats,
                "data_year": "2024",
                "note": "전국 토양오염 실태조사 요약 통계 (좌표 미포함, 지역·목적별 집계)",
            }
            self._loaded = True
            logger.info("Soil CSV loaded: %d rows", total)

        except Exception as e:
            logger.error("Failed to load soil CSV: %s", e)

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if not self._loaded or self._summary is None:
            return self._make_empty_result("토양 CSV 데이터 미확보")

        freshness = DataFreshness(
            fetched_at=datetime.now(),
            snapshot_at=datetime(2024, 12, 31),
            fallback_used=False,
            freshness="cached",
        )
        return self._make_result(self._summary, ConnectorStatus.STABLE, freshness)

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        """로컬 CSV 기반이므로 폴백 불필요 — 빈 결과 반환."""
        return self._make_empty_result(error or "No data available")
