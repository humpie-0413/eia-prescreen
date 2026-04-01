import asyncio
import logging
from typing import Any

from backend.app.connectors.air_quality import AirQualityConnector
from backend.app.connectors.base import BaseConnector, ConnectorResult
from backend.app.connectors.cultural import CulturalConnector
from backend.app.connectors.ecology import EcologyConnector
from backend.app.connectors.eia_info import EiaInfoConnector
from backend.app.connectors.facilities import FacilitiesConnector
from backend.app.connectors.geology import GeologyConnector
from backend.app.connectors.greenhouse import GreenhouseConnector
from backend.app.connectors.hydrology import HydrologyConnector
from backend.app.connectors.industry import IndustryConnector
from backend.app.connectors.land_use import LandUseConnector
from backend.app.connectors.landscape import LandscapeConnector
from backend.app.connectors.marine import MarineConnector
from backend.app.connectors.noise import NoiseConnector
from backend.app.connectors.ocean import OceanConnector
from backend.app.connectors.odor import OdorConnector
from backend.app.connectors.population import PopulationConnector
from backend.app.connectors.project_area import ProjectAreaConnector
from backend.app.connectors.radio import RadioConnector
from backend.app.connectors.soil import SoilConnector
from backend.app.connectors.species import SpeciesConnector
from backend.app.connectors.traffic import TrafficConnector
from backend.app.connectors.waste_data import WasteDataConnector
from backend.app.connectors.water_quality import WaterQualityConnector
from backend.app.connectors.weather import WeatherConnector

logger = logging.getLogger(__name__)

# 룰 엔진 필드명과 커넥터 이름 간의 별칭 매핑
# YAML 규칙이 "water.*"로 참조하지만 커넥터 이름은 "water_quality"
_FIELD_ALIASES: dict[str, str] = {
    "water_quality": "water",
    "weather": "climate",
}

# 대기관리권역 시도 (대기환경보전법 시행령)
_AIR_MANAGEMENT_ZONES = {"서울", "인천", "경기", "대전", "세종", "충남", "충북"}

# 교통영향평가 대상 사업유형 (도시교통정비촉진법)
_TRAFFIC_ASSESSMENT_TYPES = {
    "urban_dev", "industrial", "energy", "road", "railway",
    "port", "airport", "tourism", "sports", "water_resource",
}


# ── V-world 피처 헬퍼 ──────────────────────────────────────────

def _vworld_found(land_use_data: dict, layer_code: str) -> bool:
    """V-world 레이어에 피처가 존재하는지 확인한다."""
    vworld = land_use_data.get("vworld", {})
    layer = vworld.get(layer_code, {})
    return bool(layer.get("found", False) and layer.get("count", 0) > 0)


def _vworld_features(land_use_data: dict, layer_code: str) -> list[dict]:
    """V-world 레이어의 피처 속성 목록을 반환한다."""
    vworld = land_use_data.get("vworld", {})
    layer = vworld.get(layer_code, {})
    if layer.get("found") and layer.get("count", 0) > 0:
        return layer.get("features", [])
    return []


# ── 도메인별 정규화 함수 ─────────────────────────────────────

def _normalize_land_use(raw: dict, project_type: str | None) -> dict:
    """V-world 피처 → 룰 엔진이 기대하는 불리언 중첩 플래그로 변환."""
    result = {**raw}

    conservation_overlap = _vworld_found(raw, "LT_C_UQ114")
    greenbelt_overlap = _vworld_found(raw, "LT_C_UQ141")
    agricultural_overlap = _vworld_found(raw, "LT_C_UQ113")
    river_overlap = _vworld_found(raw, "LT_C_WKMSTRM")

    # 용도지역 유형 추출 — 모든 V-world 피처에서 구체적 용도지역명 수집
    # V-world 레이어별로 필드명이 다름: UQD_NM, uqd_nm, uname 등
    zone_types: list[str] = []
    zone_type = ""
    _ZONE_NAME_FIELDS = ("UQD_NM", "uqd_nm", "uname", "UNAME")
    for code, label in [
        ("LT_C_UQ111", "도시지역"), ("LT_C_UQ112", "관리지역"),
        ("LT_C_UQ113", "농림지역"), ("LT_C_UQ114", "자연환경보전지역"),
    ]:
        if _vworld_found(raw, code):
            features = _vworld_features(raw, code)
            for feat in features:
                if isinstance(feat, dict):
                    uqd = ""
                    for field in _ZONE_NAME_FIELDS:
                        uqd = feat.get(field, "")
                        if uqd:
                            break
                    if uqd and uqd not in zone_types:
                        zone_types.append(uqd)

    # zone_type: 첫 번째 값 (룰 엔진 호환)
    zone_type = zone_types[0] if zone_types else ""

    # 용도지역 상충 판단 — 보전지역·농림지역에서의 개발성 사업
    zone_conflict = False
    if project_type:
        if conservation_overlap:
            zone_conflict = True
        elif agricultural_overlap and project_type in (
            "urban_dev", "industrial", "energy", "waste",
            "port", "airport", "mining", "reclamation",
        ):
            zone_conflict = True

    result.update({
        "zone_type": zone_type,
        "zone_types": zone_types,
        "zone_conflict": zone_conflict,
        "conservation_zone_overlap": conservation_overlap,
        "greenbelt_overlap": greenbelt_overlap,
        "military_zone_overlap": False,
        "agricultural_zone_overlap": agricultural_overlap,
        "forest_conservation_overlap": False,
        "river_zone_overlap": river_overlap,
        "road_buffer_zone_overlap": False,
    })
    return result


def _normalize_ecology(
    raw: dict,
    land_use_data: dict | None = None,
    marine_data: dict | None = None,
) -> dict:
    """WMS 토지피복 → 생태 필드로 변환.

    land_use_data와 marine_data를 활용하여 보전지역/연안 인접 시 생태 등급을 보강한다.
    """
    result = {**raw}
    landcover = raw.get("landcover", {})
    l1_code = str(landcover.get("l1_code", ""))[:1]

    in_forest = l1_code == "3"
    in_wetland = l1_code == "5"

    # 생태자연도 등급 추정 (WMS 토지피복 기반)
    eco_grade = None
    if l1_code == "5":      # 습지 → 1등급 가능성 높음
        eco_grade = 1
    elif l1_code == "3":    # 산림 → 2등급 추정
        eco_grade = 2
    elif l1_code == "2":    # 농업지역 → 3등급
        eco_grade = 3

    eco_landscape = False

    # 보전지역 보강: 자연환경보전지역(LT_C_UQ114) 중첩 시 최소 1등급
    lu = land_use_data or {}
    if lu.get("conservation_zone_overlap"):
        eco_grade = min(eco_grade or 99, 1)

    # 연안+관리지역 조합: 연안 생태 민감 지역 판정
    # 해양 커넥터 데이터가 있으면(연안 인접) 생태 등급 보강
    marine = marine_data or {}
    has_marine = bool(marine and any(
        v for k, v in marine.items()
        if k not in ("marine_protected_distance_m", "coastal_wetland_overlap",
                     "fishery_zone_overlap", "beach_distance_m")
        and v not in (None, False, 0, "", {}, [])
    ))
    zone_types = lu.get("zone_types", [])
    has_conservation_mgmt = any("보전" in zt for zt in zone_types)
    has_mgmt_zone = any("관리" in zt for zt in zone_types)

    # 연안+보전관리 → 생태경관보전 Critical
    if has_marine and has_conservation_mgmt:
        eco_landscape = True
        eco_grade = min(eco_grade or 99, 1)
    # 연안+관리지역 → 최소 생태 2등급 (연안 생태계 보호 필요)
    elif has_marine and has_mgmt_zone:
        eco_grade = min(eco_grade or 99, 2)
        eco_landscape = True

    result.update({
        "eco_grade": eco_grade,
        "endangered_species_distance_m": None,
        "forest_wetland_distance_m": 0 if (in_forest or in_wetland) else None,
        "natural_park_distance_m": None,
        "baekdudaegan_distance_m": None,
        "eco_landscape_conservation_overlap": eco_landscape,
        "eco_corridor_distance_m": None,
    })
    return result


def _normalize_water(raw: dict, land_use_data: dict) -> dict:
    """수질 데이터 + V-world 하천 정보 → 수질 필드 보충."""
    result = {**raw}
    river_found = _vworld_found(land_use_data, "LT_C_WKMSTRM")

    # V-world에서 하천 피처를 찾았으면 거리 추정 (1km 버퍼 내)
    if result.get("river_distance_m") is None and river_found:
        result["river_distance_m"] = 500

    result.setdefault("water_source_protection_distance_m", None)
    result.setdefault("sensitive_water_zone", None)
    result.setdefault("total_pollution_load_area", None)
    result.setdefault("underground_water_protection_distance_m", None)
    return result


def _normalize_air_quality(raw: dict) -> dict:
    """에어코리아 데이터는 이미 올바른 형식 — 기본값만 보장."""
    result = {**raw}
    result.setdefault("pm25_annual_avg", None)
    result.setdefault("pm10_annual_avg", None)
    result.setdefault("dust_source_distance_m", None)
    result.setdefault("regulated_zone", None)
    result.setdefault("odor_management_zone", None)
    return result


def _normalize_noise(raw: dict, land_use_data: dict) -> dict:
    """소음 데이터 + V-world 건물 정보 → 소음 필드."""
    result = {**raw}
    buildings_found = _vworld_found(land_use_data, "LT_C_SPBD")

    # V-world에서 건물을 찾았으면 주거지 근접 추정
    result.setdefault(
        "residential_distance_m",
        500 if buildings_found else None,
    )
    result.setdefault("quiet_facility_distance_m", None)
    result.setdefault("noise_countermeasure_zone", None)
    result.setdefault("vibration_sensitive_distance_m", None)
    return result


def _normalize_soil(raw: dict) -> dict:
    """토양 데이터 — 위치별 특정 필드는 도출 불가, 기본값 설정."""
    result = {**raw}
    result.setdefault("contamination_risk", None)
    result.setdefault("groundwater_level_m", None)
    result.setdefault("landfill_distance_m", None)
    result.setdefault("geological_hazard_risk", None)
    return result


def _normalize_traffic(raw: dict, project_type: str | None) -> dict:
    """교통 데이터 → 교통 필드."""
    result = {**raw}
    total = raw.get("total_traffic", 0)
    result.setdefault(
        "traffic_volume_daily",
        total if total and total > 0 else None,
    )
    result.setdefault("school_route_distance_m", None)
    result.setdefault(
        "traffic_impact_assessment_required",
        True if project_type in _TRAFFIC_ASSESSMENT_TYPES else None,
    )
    result.setdefault("public_transit_distance_m", None)
    return result


def _normalize_greenhouse(raw: dict) -> dict:
    """온실가스 데이터 — 국가 통계 수준, 개별 사업 배출량 도출 불가."""
    result = {**raw}
    result.setdefault("estimated_annual_emission_tco2", None)
    result.setdefault("emission_trading_target", None)
    result.setdefault("carbon_neutral_zone", None)
    return result


def _normalize_geology(raw: dict) -> dict:
    """지형지질 데이터 → 지질 필드."""
    result = {**raw}
    overview = raw.get("overview", {})
    cut_stats = overview.get("cut_volume_m3", {})
    fill_stats = overview.get("fill_volume_m3", {})
    mean_cut = cut_stats.get("mean", 0) or 0
    mean_fill = fill_stats.get("mean", 0) or 0
    total_vol = mean_cut + mean_fill

    result.setdefault("steep_slope_risk", None)
    result.setdefault("subsidence_risk", None)
    result.setdefault(
        "cut_fill_volume_m3",
        total_vol if total_vol > 0 else None,
    )
    return result


def _normalize_population(raw: dict) -> dict:
    """인구주거 데이터 — EIA 이력 집계, 위치별 인구밀도 도출 불가."""
    result = {**raw}
    result.setdefault("population_density_per_km2", None)
    result.setdefault("vulnerable_population_ratio", None)
    result.setdefault("relocation_households", None)
    return result


def _normalize_cultural(raw: dict, land_use_data: dict) -> dict:
    """문화재 데이터 + V-world 문화재보호구역 → 문화재 필드."""
    result = {**raw}
    heritage_found = _vworld_found(land_use_data, "LT_C_AISRESC")

    result.setdefault("heritage_protection_overlap", heritage_found)
    result.setdefault(
        "buried_heritage_distance_m",
        500 if heritage_found else None,
    )
    result.setdefault("natural_monument_distance_m", None)
    return result


def _normalize_marine(raw: dict) -> dict:
    """해양 데이터 — 해양 API 응답에서 필드 추출."""
    result = {**raw}
    result.setdefault("marine_protected_distance_m", None)
    result.setdefault("coastal_wetland_overlap", False)
    result.setdefault("fishery_zone_overlap", False)
    result.setdefault("beach_distance_m", None)
    return result


def _normalize_landscape(raw: dict) -> dict:
    result = {**raw}
    result.setdefault("scenic_resource_distance_m", None)
    result.setdefault("viewpoint_impact", None)
    result.setdefault("light_pollution_sensitive", None)
    return result


def _normalize_social(raw: dict) -> dict:
    result = {**raw}
    result.setdefault("repeated_complaints", None)
    result.setdefault("similar_project_supplement_count", None)
    result.setdefault("environmental_justice_vulnerable", None)
    return result


def _normalize_hazard(raw: dict) -> dict:
    result = {**raw}
    result.setdefault("hazardous_facility_distance_m", None)
    result.setdefault("natural_disaster_risk_zone", None)
    result.setdefault("seismic_assessment_required", None)
    return result


def _normalize_waste(raw: dict) -> dict:
    result = {**raw}
    result.setdefault("estimated_construction_waste_ton", None)
    result.setdefault("waste_facility_capacity_shortage", None)
    return result


def _normalize_odor(raw: dict) -> dict:
    """악취 데이터 — 악취관리지역 중첩, 악취배출시설, 악취 초과 여부."""
    result = {**raw}
    result.setdefault("management_area_overlap", False)
    result.setdefault("nearest_odor_facility_m", None)
    result.setdefault("odor_exceed", False)
    result.setdefault("station_count", 0)
    return result


def _normalize_radio(raw: dict) -> dict:
    """전파환경 데이터 — 전파간섭 리스크, 레이더/방송탑 거리."""
    result = {**raw}
    result.setdefault("radio_interference_risk", False)
    result.setdefault("radar_facility_distance_m", None)
    result.setdefault("broadcasting_tower_distance_m", None)
    return result


def _normalize_sunshine(climate_data: dict, project_type: str | None) -> dict:
    """일조장해 검토 필요 여부 판단 (도시개발 사업에서만 트리거)."""
    result = {}
    result["sunshine_hours"] = climate_data.get("sunshine_hours")
    result["solar_radiation"] = climate_data.get("solar_radiation")
    # 도시개발(고층 건물 포함 가능) 사업에서 일조권 검토 필요
    result["sunshine_review_required"] = project_type in ("urban_dev",)
    return result


def _normalize_industry(raw: dict) -> dict:
    """산업 통계 — 산업단지 거리, 산업밀도."""
    result = {**raw}
    result.setdefault("industrial_complex_distance_m", None)
    result.setdefault("industrial_complex_name", None)
    result.setdefault("industry_density", None)
    return result


def _normalize_facilities(raw: dict) -> dict:
    """위락시설 — 시설 수, 거리, 밀집 여부."""
    result = {**raw}
    result.setdefault("recreation_facility_count", 0)
    result.setdefault("recreation_facility_distance_m", None)
    result.setdefault("recreation_density_area", False)
    return result


def _normalize_species(raw: dict) -> dict:
    """멸종위기종 데이터 — 종 목록, 등급별 존재 여부."""
    result = {**raw}
    result.setdefault("species_list", [])
    result.setdefault("species_count", 0)
    result.setdefault("has_endangered_grade_1", False)
    result.setdefault("has_endangered_grade_2", False)
    result.setdefault("endangered_species_distance_m", None)
    return result


def _normalize_hydrology(raw: dict) -> dict:
    """수리·수문 데이터 — 수위, 유량, 홍수 위험."""
    result = {**raw}
    result.setdefault("flood_risk_zone", False)
    result.setdefault("low_flow_section", False)
    result.setdefault("river_name", None)
    result.setdefault("water_level", None)
    result.setdefault("flow_rate", None)
    return result


def _normalize_ocean(raw: dict) -> dict:
    """해양관측 데이터 — 수심, 조류, 조위."""
    result = {**raw}
    result.setdefault("depth", None)
    result.setdefault("tidal_current", None)
    result.setdefault("tide_level", None)
    result.setdefault("tidal_impact_review_needed", False)
    result.setdefault("depth_change_expected", False)
    return result


def _normalize_waste_data(raw: dict) -> dict:
    """폐기물 발생현황 — 발생량, 처리량, 처리시설."""
    result = {**raw}
    result.setdefault("waste_generation_ton_day", None)
    result.setdefault("waste_treatment_ton_day", None)
    result.setdefault("treatment_capacity_ratio", None)
    result.setdefault("facility_count", 0)
    return result


# ── 전체 정규화 ──────────────────────────────────────────────

def _normalize_spatial_data(
    spatial: dict[str, Any],
    project_type: str | None = None,
) -> dict[str, Any]:
    """커넥터 raw 데이터를 룰 엔진이 기대하는 필드 구조로 정규화한다.

    각 도메인의 데이터에 룰 YAML이 참조하는 필드를 추가한다.
    실제 데이터에서 유도 가능한 필드는 값을 설정하고,
    유도 불가능한 필드는 None으로 둔다 (룰이 트리거되지 않음).
    """
    land_use = spatial.get("land_use", {})

    # 1) V-world 피처 기반 도메인
    spatial["land_use"] = _normalize_land_use(land_use, project_type)
    spatial["ecology"] = _normalize_ecology(
        spatial.get("ecology", {}),
        land_use_data=spatial["land_use"],
        marine_data=spatial.get("marine", {}),
    )

    # water는 water_quality 별칭
    water_raw = spatial.get("water", spatial.get("water_quality", {}))
    water_norm = _normalize_water(water_raw, spatial["land_use"])
    spatial["water"] = water_norm
    spatial["water_quality"] = water_norm

    # 2) 이미 정규화된 도메인
    spatial["air_quality"] = _normalize_air_quality(
        spatial.get("air_quality", {})
    )

    # 3) CSV/로컬 데이터 기반 도메인
    spatial["noise"] = _normalize_noise(
        spatial.get("noise", {}), spatial["land_use"]
    )
    spatial["soil"] = _normalize_soil(spatial.get("soil", {}))
    spatial["traffic"] = _normalize_traffic(
        spatial.get("traffic", {}), project_type
    )
    spatial["greenhouse"] = _normalize_greenhouse(
        spatial.get("greenhouse", {})
    )
    spatial["geology"] = _normalize_geology(spatial.get("geology", {}))
    spatial["population"] = _normalize_population(
        spatial.get("population", {})
    )

    # 4) 커넥터 미포함 도메인 (V-world/문맥에서 유도)
    spatial["cultural"] = _normalize_cultural(
        spatial.get("cultural", {}), spatial["land_use"]
    )
    spatial["marine"] = _normalize_marine(spatial.get("marine", {}))
    spatial["landscape"] = _normalize_landscape(
        spatial.get("landscape", {})
    )
    spatial["social"] = _normalize_social(spatial.get("social", {}))
    spatial["hazard"] = _normalize_hazard(spatial.get("hazard", {}))
    spatial["waste"] = _normalize_waste(spatial.get("waste", {}))

    # 5) B-1~B-3 신규 도메인
    spatial["odor"] = _normalize_odor(spatial.get("odor", {}))
    spatial["radio"] = _normalize_radio(spatial.get("radio", {}))
    spatial["industry"] = _normalize_industry(spatial.get("industry", {}))
    spatial["facilities"] = _normalize_facilities(spatial.get("facilities", {}))

    # 6) B-4~B-6 신규 도메인
    spatial["species"] = _normalize_species(spatial.get("species", {}))
    spatial["hydrology"] = _normalize_hydrology(spatial.get("hydrology", {}))
    spatial["ocean"] = _normalize_ocean(spatial.get("ocean", {}))
    spatial["waste_data"] = _normalize_waste_data(spatial.get("waste_data", {}))

    # climate(weather) 기반 일조장해 판단
    climate_data = spatial.get("climate", spatial.get("weather", {}))
    sunshine_norm = _normalize_sunshine(climate_data, project_type)
    # climate 도메인에 일조 필드 병합
    if "climate" in spatial:
        spatial["climate"].update(sunshine_norm)
    else:
        spatial["climate"] = sunshine_norm

    return spatial


class DataFetcher:
    """모든 커넥터를 비동기 병렬 호출하여 공간 데이터를 수집한다."""

    def __init__(self) -> None:
        self._connectors: list[BaseConnector] = [
            LandUseConnector(),
            EcologyConnector(),
            AirQualityConnector(),
            WaterQualityConnector(),
            SoilConnector(),
            NoiseConnector(),
            PopulationConnector(),
            ProjectAreaConnector(),
            EiaInfoConnector(),
            MarineConnector(),
            GeologyConnector(),
            GreenhouseConnector(),
            WeatherConnector(),
            TrafficConnector(),
            OdorConnector(),
            RadioConnector(),
            IndustryConnector(),
            FacilitiesConnector(),
            SpeciesConnector(),
            HydrologyConnector(),
            OceanConnector(),
            WasteDataConnector(),
        ]

    @property
    def connectors(self) -> list[BaseConnector]:
        return self._connectors

    async def fetch_all(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
    ) -> dict[str, ConnectorResult]:
        """모든 커넥터를 병렬 호출한다.

        Args:
            lng: 경도
            lat: 위도
            buffer_m: 버퍼 거리 (미터)

        Returns:
            {connector_name: ConnectorResult} 딕셔너리
        """
        async def _fetch_with_timeout(conn: BaseConnector) -> ConnectorResult:
            try:
                return await asyncio.wait_for(conn.fetch(lng, lat, buffer_m), timeout=45)
            except asyncio.TimeoutError:
                logger.warning("Connector %s timed out after 45s", conn.name)
                return conn._make_empty_result("Timeout after 45s")

        tasks = [_fetch_with_timeout(conn) for conn in self._connectors]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, ConnectorResult] = {}
        for conn, result in zip(self._connectors, raw_results):
            if isinstance(result, Exception):
                logger.error("Connector %s raised: %s", conn.name, result)
                results[conn.name] = conn._make_empty_result(str(result))
            else:
                results[conn.name] = result

        return results

    async def fetch_all_as_spatial_data(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        project_type: str | None = None,
    ) -> dict[str, Any]:
        """fetch_all 결과를 룰 엔진이 사용할 수 있는 정규화된 dict로 변환한다.

        Returns:
            {domain_name: data_dict} — 룰 엔진이 "domain.field" 형태로 접근 가능
        """
        connector_results = await self.fetch_all(lng, lat, buffer_m)

        spatial: dict[str, Any] = {}
        for name, result in connector_results.items():
            if result.data is not None:
                spatial[name] = result.data
            else:
                spatial[name] = {}

        # 필드 별칭 추가 (water_quality → water, weather → climate)
        for original, alias in _FIELD_ALIASES.items():
            if original in spatial and alias not in spatial:
                spatial[alias] = spatial[original]

        # 커넥터 raw 데이터를 룰 엔진 필드로 정규화
        spatial = _normalize_spatial_data(spatial, project_type)

        return spatial

    def get_status_summary(
        self,
        results: dict[str, ConnectorResult],
    ) -> list[dict]:
        """커넥터별 상태 요약을 반환한다."""
        summary = []
        for conn in self._connectors:
            r = results.get(conn.name)
            summary.append({
                "name": conn.name,
                "tier": conn.tier.value,
                "description": conn.description,
                "status": r.status.value if r else "unknown",
                "freshness": r.freshness.model_dump() if r else None,
                "has_data": r.data is not None if r else False,
                "error": r.error if r else None,
            })
        return summary
