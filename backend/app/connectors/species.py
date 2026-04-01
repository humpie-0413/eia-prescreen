"""멸종위기종 커넥터 (C계층 — 정적 CSV 데이터).

데이터 소스: 국립생물자원관 멸종위기종 CSV (267종, I급60/II급207)
생태자연도 등급과 조합하여 해당 지역에서 발견 가능한 종 추정
"""

import csv
import logging
from pathlib import Path
from typing import Any

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    DataTier,
)

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "static"
_CSV_PATH = _STATIC_DIR / "endangered_species.csv"

# 메모리 캐시 (프로세스 수명 동안 유지)
_SPECIES_DATA: list[dict] | None = None


def _load_species() -> list[dict]:
    """CSV 로딩 → 메모리 캐시."""
    global _SPECIES_DATA
    if _SPECIES_DATA is not None:
        return _SPECIES_DATA

    species = []
    if not _CSV_PATH.exists():
        logger.warning("Endangered species CSV not found: %s", _CSV_PATH)
        _SPECIES_DATA = []
        return _SPECIES_DATA

    with open(_CSV_PATH, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            _SPECIES_DATA = []
            return _SPECIES_DATA

        # 헤더: 분류군, 등급, 국명, 학명, 고유종, 국가적색목록, 세계자연보전연맹
        for row in reader:
            if len(row) < 4:
                continue
            taxon = row[0].strip().strip('"')
            grade_raw = row[1].strip().strip('"')
            name = row[2].strip().strip('"')
            scientific = row[3].strip().strip('"')
            endemic = row[4].strip().strip('"') if len(row) > 4 else ""
            red_list_kr = row[5].strip().strip('"') if len(row) > 5 else ""
            red_list_iucn = row[6].strip().strip('"') if len(row) > 6 else ""

            grade = 1 if grade_raw == "I" else (2 if grade_raw == "II" else None)

            species.append({
                "name": name,
                "scientific_name": scientific,
                "grade": grade,
                "grade_label": f"멸종위기 {grade_raw}급" if grade else "",
                "taxon": taxon,
                "endemic": endemic,
                "red_list_kr": red_list_kr,
                "red_list_iucn": red_list_iucn,
            })

    _SPECIES_DATA = species
    logger.info("Loaded %d endangered species from CSV", len(species))
    return _SPECIES_DATA


def _filter_by_eco_grade(
    eco_grade: int | None,
) -> list[dict]:
    """생태자연도 등급에 따라 발견 가능한 종 필터링.

    - 1등급: I급 전체 + II급 주요종 (포유류, 조류, 양서·파충류)
    - 2등급: II급 일부 (조류, 어류)
    - 3등급 / None: II급 소수 (조류만)
    """
    all_species = _load_species()
    if not all_species:
        return []

    # 주요 분류군 우선순위
    priority_taxons_1 = {"포유류", "조류", "양서파충류", "양서·파충류"}
    priority_taxons_2 = {"조류", "어류"}

    if eco_grade == 1:
        # I급 전체 + II급 중 포유류/조류/양서파충류
        grade1 = [s for s in all_species if s["grade"] == 1]
        grade2_priority = [
            s for s in all_species
            if s["grade"] == 2 and s["taxon"] in priority_taxons_1
        ]
        return grade1 + grade2_priority[:20]

    if eco_grade == 2:
        # II급 중 조류/어류
        return [
            s for s in all_species
            if s["grade"] == 2 and s["taxon"] in priority_taxons_2
        ][:30]

    # 3등급 또는 등급 없음: 조류만 일부
    return [
        s for s in all_species
        if s["grade"] == 2 and s["taxon"] == "조류"
    ][:10]


class SpeciesConnector(BaseConnector):
    name = "species"
    tier = DataTier.C
    description = "국립생물자원관 멸종위기종 — 267종 (I급60/II급207)"

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 5000,
        **kwargs: Any,
    ) -> ConnectorResult:
        eco_grade = kwargs.get("eco_grade")
        species = _filter_by_eco_grade(eco_grade)

        all_data = _load_species()
        total_grade1 = sum(1 for s in all_data if s["grade"] == 1)
        total_grade2 = sum(1 for s in all_data if s["grade"] == 2)

        has_grade_1 = any(s["grade"] == 1 for s in species)
        has_grade_2 = any(s["grade"] == 2 for s in species)

        data = {
            "species_list": species[:20],
            "species_count": len(species),
            "total_species_in_db": len(all_data),
            "total_grade_1": total_grade1,
            "total_grade_2": total_grade2,
            "has_endangered_grade_1": has_grade_1,
            "has_endangered_grade_2": has_grade_2,
            "endangered_species_distance_m": 0 if has_grade_1 else None,
            "eco_grade_used": eco_grade,
            "source": "국립생물자원관 멸종위기종 CSV (2024.12.31 기준)",
        }

        return self._make_result(data)
