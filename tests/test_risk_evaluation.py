"""Rule validation matrix — 양평/세종/보령 3개 시나리오 테스트.

각 시나리오별 기대 리스크 카드 vs 실제 출력을 비교한다.
테스트 픽스처로 spatial_data를 직접 제공하여 룰 엔진을 단위 테스트한다.
"""

from __future__ import annotations

import pytest

from backend.app.services.checklist_generator import ChecklistGenerator
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.risk_engine import RiskEngine

# ── 공용 ────────────────────────────────────────────────────

SCENARIOS = ["yangpyeong", "sejong", "boryeong"]

# 시나리오별 프로젝트 정보 (테스트 픽스처)
PROJECT_INFOS = {
    "yangpyeong": {
        "project_name": "양평 국도 우회도로",
        "project_type": "road",
        "project_scale": "L=2.1km, W=20m",
        "address": "경기도 양평군 양평읍",
    },
    "sejong": {
        "project_name": "세종 행복도시 3-2생활권",
        "project_type": "housing",
        "project_scale": "A=850,000m²",
        "address": "세종특별자치시 반곡동",
    },
    "boryeong": {
        "project_name": "보령 복합화력발전소",
        "project_type": "power_plant",
        "project_scale": "1,000MW",
        "address": "충남 보령시 오천면",
    },
}

# 시나리오별 공간 데이터 (테스트 픽스처 — 룰 엔진이 참조하는 필드)
SPATIAL_DATA = {
    "yangpyeong": {
        "land_use": {
            "zone_type": "농림지역",
            "zone_conflict": False,
            "conservation_zone_overlap": False,
            "greenbelt_overlap": False,
            "military_zone_overlap": False,
            "agricultural_zone_overlap": True,  # LAND-005
            "forest_conservation_overlap": False,
            "river_zone_overlap": False,
            "road_buffer_zone_overlap": False,
        },
        "ecology": {
            "eco_grade": 2,
            "endangered_species_distance_m": 800,  # ECO-002 (< 1000)
            "forest_wetland_distance_m": 300,  # ECO-003 (< 500)
            "natural_park_distance_m": 2500,
            "baekdudaegan_distance_m": 15000,
            "eco_landscape_conservation_overlap": False,
            "eco_corridor_distance_m": 500,
        },
        "water": {
            "river_distance_m": 80,  # WAT-001 (< 100)
            "water_source_protection_distance_m": 5000,
            "sensitive_water_zone": True,  # WAT-003
            "total_pollution_load_area": False,
            "underground_water_protection_distance_m": 500,
        },
        "air_quality": {
            "pm25_annual_avg": 22.5,  # AIR-001 NOT triggered (< 35)
            "dust_source_distance_m": 5000,
            "regulated_zone": False,
            "pm10_annual_avg": 42,
            "odor_management_zone": False,
        },
        "noise": {
            "residential_distance_m": 250,  # NOI-001 (< 300)
            "quiet_facility_distance_m": 350,
            "noise_countermeasure_zone": False,
            "vibration_sensitive_distance_m": 300,
        },
        "soil": {
            "contamination_risk": False,
            "groundwater_level_m": 5,
            "landfill_distance_m": 3000,
            "geological_hazard_risk": False,
        },
        "cultural": {
            "heritage_protection_overlap": False,
            "buried_heritage_distance_m": 500,
            "natural_monument_distance_m": 2000,
        },
        "landscape": {
            "scenic_resource_distance_m": 800,
            "viewpoint_impact": False,
            "light_pollution_sensitive": False,
        },
        "social": {
            "repeated_complaints": 1,
            "similar_project_supplement_count": 1,
            "environmental_justice_vulnerable": False,
        },
        "traffic": {},
        "population": {},
        "marine": {},
        "greenhouse": {},
        "geology": {},
        "weather": {},
        "climate": {},
    },
    "sejong": {
        "land_use": {
            "zone_type": "도시지역",
            "zone_conflict": False,
            "conservation_zone_overlap": False,
            "greenbelt_overlap": False,
            "military_zone_overlap": False,
            "agricultural_zone_overlap": False,
            "forest_conservation_overlap": False,
            "river_zone_overlap": False,
            "road_buffer_zone_overlap": False,
        },
        "ecology": {
            "eco_grade": 3,  # ECO-001 NOT triggered (grade != 1)
            "endangered_species_distance_m": 3000,
            "forest_wetland_distance_m": 800,
            "natural_park_distance_m": 5000,
            "baekdudaegan_distance_m": 50000,
            "eco_landscape_conservation_overlap": False,
            "eco_corridor_distance_m": 1000,
        },
        "water": {
            "river_distance_m": 200,
            "water_source_protection_distance_m": 12000,  # WAT-002 NOT triggered (> 500)
            "sensitive_water_zone": False,
            "total_pollution_load_area": True,  # WAT-004
            "underground_water_protection_distance_m": 500,
        },
        "air_quality": {
            "pm25_annual_avg": 28,
            "dust_source_distance_m": 3000,
            "regulated_zone": True,  # AIR-003
            "pm10_annual_avg": 45,
            "odor_management_zone": False,
        },
        "noise": {
            "residential_distance_m": 80,   # NOI-001 (< 300)
            "quiet_facility_distance_m": 150,  # NOI-002 (< 200)
            "noise_countermeasure_zone": False,
            "vibration_sensitive_distance_m": 200,
        },
        "soil": {
            "contamination_risk": False,
            "groundwater_level_m": 4,
            "landfill_distance_m": 2000,
            "geological_hazard_risk": False,
        },
        "cultural": {
            "heritage_protection_overlap": False,
            "buried_heritage_distance_m": 500,
            "natural_monument_distance_m": 3000,
        },
        "landscape": {
            "scenic_resource_distance_m": 1000,
            "viewpoint_impact": False,
            "light_pollution_sensitive": False,
        },
        "social": {
            "repeated_complaints": 4,  # SOC-001 (>= 3)
            "similar_project_supplement_count": 1,
            "environmental_justice_vulnerable": False,
        },
        "traffic": {},
        "population": {},
        "marine": {},
        "greenhouse": {},
        "geology": {},
        "weather": {},
        "climate": {},
    },
    "boryeong": {
        "land_use": {
            "zone_type": "관리지역",
            "zone_conflict": True,        # LAND-001 (critical)
            "conservation_zone_overlap": False,
            "greenbelt_overlap": False,
            "military_zone_overlap": True,  # LAND-004 (major)
            "agricultural_zone_overlap": True,  # LAND-005 (major)
            "forest_conservation_overlap": True,  # LAND-006 (critical)
            "river_zone_overlap": True,     # LAND-007 (major)
            "road_buffer_zone_overlap": True,  # LAND-008 (review)
        },
        "ecology": {
            "eco_grade": 1,               # ECO-001 (critical)
            "endangered_species_distance_m": 500,  # ECO-002 (< 1000)
            "forest_wetland_distance_m": 200,    # ECO-003 (< 500)
            "natural_park_distance_m": 800,  # ECO-004 (< 1000)
            "baekdudaegan_distance_m": 5000,
            "eco_landscape_conservation_overlap": False,
            "eco_corridor_distance_m": 150,  # ECO-007 (< 200)
        },
        "water": {
            "river_distance_m": 50,         # WAT-001 (< 100)
            "water_source_protection_distance_m": 450,  # WAT-002 (< 500, critical)
            "sensitive_water_zone": True,   # WAT-003
            "total_pollution_load_area": True,  # WAT-004
            "underground_water_protection_distance_m": 200,  # WAT-005 (< 300)
        },
        "air_quality": {
            "pm25_annual_avg": 38.2,       # AIR-001 (> 35)
            "dust_source_distance_m": 1500,  # AIR-002 (< 2000)
            "regulated_zone": True,         # AIR-003
            "pm10_annual_avg": 55,          # AIR-004 (> 50)
            "odor_management_zone": False,
        },
        "noise": {
            "residential_distance_m": 120,   # NOI-001 (< 300)
            "quiet_facility_distance_m": 180,  # NOI-002 (< 200)
            "noise_countermeasure_zone": False,
            "vibration_sensitive_distance_m": 80,  # NOI-004 (< 100)
        },
        "soil": {
            "contamination_risk": True,     # SOI-001
            "groundwater_level_m": 2.5,     # SOI-002 (< 3)
            "landfill_distance_m": 350,     # SOI-003 (< 500)
            "geological_hazard_risk": True,  # SOI-004
        },
        "cultural": {
            "heritage_protection_overlap": False,
            "buried_heritage_distance_m": 150,  # CUL-002 (< 300)
            "natural_monument_distance_m": 800,
        },
        "landscape": {
            "scenic_resource_distance_m": 300,  # LAN-001 (< 500)
            "viewpoint_impact": True,       # LAN-002
            "light_pollution_sensitive": True,  # LAN-003
        },
        "social": {
            "repeated_complaints": 5,       # SOC-001 (>= 3)
            "similar_project_supplement_count": 3,  # SOC-002 (>= 2)
            "environmental_justice_vulnerable": True,  # SOC-003
        },
        "traffic": {},
        "population": {},
        "marine": {},
        "greenhouse": {},
        "geology": {},
        "weather": {},
        "climate": {},
    },
}


@pytest.fixture(scope="module")
def engine() -> RiskEngine:
    e = RiskEngine()
    e.load_rules()
    return e


@pytest.fixture(scope="module")
def matcher() -> RegulationMatcher:
    return RegulationMatcher()


@pytest.fixture(scope="module")
def checklist_gen() -> ChecklistGenerator:
    return ChecklistGenerator()


@pytest.fixture(scope="module")
def all_results(engine, matcher):
    """3개 시나리오의 평가 결과를 사전 계산한다."""
    out = {}
    for scenario in SCENARIOS:
        project_info = PROJECT_INFOS[scenario]
        spatial = SPATIAL_DATA[scenario]
        risks = engine.evaluate(project_info, spatial)
        regs = matcher.match(project_info, spatial)
        out[scenario] = {"risks": risks, "regs": regs, "spatial": spatial}
    return out


# ── 규칙 로드 테스트 ────────────────────────────────────────


def test_rules_loaded(engine: RiskEngine) -> None:
    assert len(engine.rules) == 77, f"Expected 77 rules, got {len(engine.rules)}"


def test_rules_cover_all_domains(engine: RiskEngine) -> None:
    domains = {r.rule_id.split("-")[0] for r in engine.rules}
    expected = {
        "LAND", "ECO", "AIR", "WAT", "NOI", "SOI", "LAN", "CUL", "SOC",
        "GEO", "GHG", "HAZ", "MAR", "POP", "TRF", "WST",
        "ODR", "SUN", "RAD", "IND", "REC",
        "HYD", "OCN",
    }
    assert domains == expected


# ── 양평 (도로) ─────────────────────────────────────────────


class TestYangpyeong:
    """양평 도로 시나리오: 농업지역 + 생태2등급 + 수변구역."""

    def test_risk_count(self, all_results) -> None:
        risks = all_results["yangpyeong"]["risks"]
        assert len(risks) >= 5, f"Expected at least 5 risk cards, got {len(risks)}"

    def test_no_critical(self, all_results) -> None:
        """양평 도로는 critical 리스크가 없어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        criticals = [r for r in risks if r.severity == "critical"]
        assert len(criticals) == 0, f"Unexpected criticals: {[r.rule_id for r in criticals]}"

    def test_agricultural_zone_rule(self, all_results) -> None:
        """LAND-005 농업진흥지역 중첩이 트리거되어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "LAND-005" in rule_ids

    def test_endangered_species_rule(self, all_results) -> None:
        """ECO-002 멸종위기종 인접 (800m < 1000m)이 트리거되어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "ECO-002" in rule_ids

    def test_water_sensitive_zone(self, all_results) -> None:
        """WAT-003 팔당상수원 수변구역이 트리거되어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "WAT-003" in rule_ids

    def test_noise_residential(self, all_results) -> None:
        """NOI-001 주거지역 인접 (250m < 300m)이 트리거되어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "NOI-001" in rule_ids

    def test_no_air_quality_exceed(self, all_results) -> None:
        """AIR-001 PM2.5 초과 없음 (22.5 < 35)."""
        risks = all_results["yangpyeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "AIR-001" not in rule_ids

    def test_severity_order(self, all_results) -> None:
        """결과가 severity 순서대로 정렬되어야 한다."""
        risks = all_results["yangpyeong"]["risks"]
        order = {"critical": 0, "major": 1, "review": 2, "info": 3}
        severities = [order.get(r.severity, 99) for r in risks]
        assert severities == sorted(severities)

    def test_regulation_count(self, all_results) -> None:
        regs = all_results["yangpyeong"]["regs"]
        assert len(regs) >= 3


# ── 세종 (주거) ─────────────────────────────────────────────


class TestSejong:
    """세종 주거 시나리오: 도시지역 + 대기규제 + 소음 인접."""

    def test_risk_count(self, all_results) -> None:
        risks = all_results["sejong"]["risks"]
        assert len(risks) >= 3

    def test_no_critical(self, all_results) -> None:
        """세종 주거는 critical 리스크가 없어야 한다."""
        risks = all_results["sejong"]["risks"]
        criticals = [r for r in risks if r.severity == "critical"]
        assert len(criticals) == 0

    def test_air_regulated_zone(self, all_results) -> None:
        """AIR-003 대기관리권역 포함이 트리거되어야 한다."""
        risks = all_results["sejong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "AIR-003" in rule_ids

    def test_noise_rules(self, all_results) -> None:
        """NOI-001, NOI-002 둘 다 트리거되어야 한다 (80m, 150m)."""
        risks = all_results["sejong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "NOI-001" in rule_ids
        assert "NOI-002" in rule_ids

    def test_social_complaints(self, all_results) -> None:
        """SOC-001 반복민원 (4 >= 3) 트리거."""
        risks = all_results["sejong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "SOC-001" in rule_ids

    def test_no_eco_grade_critical(self, all_results) -> None:
        """ECO-001 생태1등급은 트리거 안 됨 (등급 3)."""
        risks = all_results["sejong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "ECO-001" not in rule_ids

    def test_no_water_critical(self, all_results) -> None:
        """WAT-002 상수원보호 안 됨 (12000m > 500m)."""
        risks = all_results["sejong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "WAT-002" not in rule_ids


# ── 보령 (발전소) ───────────────────────────────────────────


class TestBoryeong:
    """보령 발전소 시나리오: 생태1등급 + 용도상충 + 상수원 인접 + 복합 리스크."""

    def test_risk_count(self, all_results) -> None:
        risks = all_results["boryeong"]["risks"]
        assert len(risks) >= 15, f"Expected at least 15 risk cards, got {len(risks)}"

    def test_critical_count(self, all_results) -> None:
        """보령은 critical 리스크가 4개 있어야 한다."""
        risks = all_results["boryeong"]["risks"]
        criticals = [r for r in risks if r.severity == "critical"]
        assert len(criticals) == 4
        critical_ids = {r.rule_id for r in criticals}
        assert critical_ids == {"ECO-001", "LAND-001", "LAND-006", "WAT-002"}

    def test_eco_grade_1(self, all_results) -> None:
        """ECO-001 생태자연도 1등급 직접 중첩."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "ECO-001" in rule_ids

    def test_zone_conflict(self, all_results) -> None:
        """LAND-001 용도지역 상충."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "LAND-001" in rule_ids

    def test_water_source_protection(self, all_results) -> None:
        """WAT-002 상수원보호구역 인접 (450m < 500m)."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "WAT-002" in rule_ids

    def test_pm25_exceed(self, all_results) -> None:
        """AIR-001 PM2.5 초과 (38.2 > 35)."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "AIR-001" in rule_ids

    def test_military_zone(self, all_results) -> None:
        """LAND-004 군사시설보호구역 중첩."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "LAND-004" in rule_ids

    def test_soil_contamination(self, all_results) -> None:
        """SOI-001 토양오염 우려."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "SOI-001" in rule_ids

    def test_buried_heritage(self, all_results) -> None:
        """CUL-002 매장문화재 인접 (150m < 300m)."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "CUL-002" in rule_ids

    def test_landscape_both_rules(self, all_results) -> None:
        """LAN-001 + LAN-002 둘 다 트리거."""
        risks = all_results["boryeong"]["risks"]
        rule_ids = [r.rule_id for r in risks]
        assert "LAN-001" in rule_ids
        assert "LAN-002" in rule_ids

    def test_regulation_count(self, all_results) -> None:
        regs = all_results["boryeong"]["regs"]
        assert len(regs) >= 6

    def test_eco_grade_1_regulation(self, all_results) -> None:
        regs = all_results["boryeong"]["regs"]
        eco_regs = [r for r in regs if "생태자연도 1등급" in r.regulation_name]
        assert len(eco_regs) >= 1

    def test_military_regulation(self, all_results) -> None:
        regs = all_results["boryeong"]["regs"]
        mil_regs = [r for r in regs if "군사" in r.regulation_name]
        assert len(mil_regs) >= 1


# ── 체크리스트 생성 테스트 ──────────────────────────────────


class TestChecklist:
    """체크리스트 생성 통합 테스트."""

    def test_checklist_sections(self, all_results, checklist_gen) -> None:
        """보령 시나리오: critical/major/review 3개 섹션 + regulation 섹션."""
        risks = all_results["boryeong"]["risks"]
        regs = all_results["boryeong"]["regs"]
        cl = checklist_gen.generate(risks, regs, screening_id="test-boryeong")

        section_names = [s.section_name for s in cl.sections]
        assert "즉시 확인 필요 (Critical)" in section_names
        assert "주요 검토 항목 (Major)" in section_names

    def test_checklist_items_numbered(self, all_results, checklist_gen) -> None:
        risks = all_results["boryeong"]["risks"]
        cl = checklist_gen.generate(risks, screening_id="test")

        all_ids = [item.id for s in cl.sections for item in s.items]
        # IDs are sequential 1..N
        assert all_ids == list(range(1, len(all_ids) + 1))
        assert cl.total_items == len(all_ids)

    def test_checklist_pdf_structure(self, all_results, checklist_gen) -> None:
        risks = all_results["sejong"]["risks"]
        cl = checklist_gen.generate(risks, screening_id="test-sejong")
        pdf = checklist_gen.to_pdf_structure(cl)

        assert pdf["title"] == "현장조사 체크리스트"
        assert pdf["screening_id"] == "test-sejong"
        assert len(pdf["sections"]) > 0

    def test_empty_input(self, checklist_gen) -> None:
        cl = checklist_gen.generate([], [])
        assert cl.total_items == 0
        assert len(cl.sections) == 0
