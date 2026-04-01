"""사업구역 커넥터 (C계층 — 로컬 DBF 데이터).

데이터 소스: 국립환경과학원 환경영향평가 사업구역정보 (BSNS_AREA.dbf)
- 2,766건 사업구역 속성 데이터 (사업명, 유형, 면적 등)
- SHP 지오메트리는 PostGIS 연동 시 활용 예정
"""

import logging
import struct
from pathlib import Path
from typing import Any

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataTier,
    DataFreshness,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "new"
_DBF_PATH = (
    _DATA_DIR
    / "기후에너지환경부 국립환경과학원_환경영향평가  사업구역정보_20241216"
    / "BSNS_AREA"
    / "BSNS_AREA.dbf"
)


def _read_dbf(path: Path) -> list[dict[str, str]]:
    """DBF 파일을 읽어 딕셔너리 리스트로 반환한다."""
    rows: list[dict[str, str]] = []
    with open(path, "rb") as f:
        numrec, lenheader = struct.unpack("<xxxxIH22x", f.read(32))
        numfields = (lenheader - 33) // 32
        fields: list[tuple[str, int]] = []
        for _ in range(numfields):
            name = f.read(11).replace(b"\x00", b"").decode("ascii")
            f.read(1)  # type
            f.read(4)  # reserved
            flen = struct.unpack("B", f.read(1))[0]
            f.read(15)
            fields.append((name, flen))
        f.read(1)  # terminator

        for _ in range(numrec):
            f.read(1)  # deletion flag
            row: dict[str, str] = {}
            for name, flen in fields:
                raw = f.read(flen)
                try:
                    row[name] = raw.decode("cp949").strip()
                except Exception:
                    row[name] = raw.decode("utf-8", errors="replace").strip()
            rows.append(row)
    return rows


class ProjectAreaConnector(BaseConnector):
    name = "project_area"
    tier = DataTier.C
    description = "EIASS 사업구역정보 — 사업구역 경계·면적·토지피복"

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None
        self._load_data()

    def _load_data(self) -> None:
        """DBF 파일에서 사업구역 데이터를 로드한다."""
        if not _DBF_PATH.exists():
            logger.warning("Project area DBF not found: %s", _DBF_PATH)
            return

        try:
            records = _read_dbf(_DBF_PATH)
            # 사업유형별 집계
            by_type: dict[str, int] = {}
            total_area = 0.0
            areas: list[float] = []

            for rec in records:
                btype = rec.get("BSNS_OD", "기타")
                by_type[btype] = by_type.get(btype, 0) + 1
                try:
                    area = float(rec.get("SHAPE_Area", 0))
                    total_area += area
                    areas.append(area)
                except (ValueError, TypeError):
                    pass

            avg_area = total_area / len(areas) if areas else 0
            # 상위 사업유형
            sorted_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)

            self._data = {
                "source": "EIASS 사업구역정보 (BSNS_AREA.dbf)",
                "total_projects": len(records),
                "total_area_sqm": round(total_area, 1),
                "avg_area_sqm": round(avg_area, 1),
                "by_project_type": dict(sorted_types[:15]),
                "sample_projects": [
                    {
                        "mgt_no": r.get("MGTNO", ""),
                        "name": r.get("BSNS_NM", ""),
                        "type": r.get("BSNS_OD", ""),
                        "area_sqm": round(float(r.get("SHAPE_Area", 0)), 1),
                    }
                    for r in records[:20]
                ],
            }
            logger.info(
                "Loaded %d project areas from DBF", len(records)
            )
        except Exception:
            logger.exception("Failed to load project area DBF")

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        if self._data is None:
            return self._make_error("사업구역 데이터 파일을 찾을 수 없습니다")

        return self._make_result(
            self._data,
            ConnectorStatus.STABLE,
            DataFreshness(
                fetched_at=None,
                snapshot_at="2024-12-16",
                fallback_used=False,
                freshness="cached",
            ),
        )
