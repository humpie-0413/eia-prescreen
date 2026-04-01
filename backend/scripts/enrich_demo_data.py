"""데모 시나리오 mock_data.json 실데이터 교체 스크립트.

각 시나리오의 mock_data.json을 14개 커넥터 전체가 포함된 형태로 갱신한다.
DeepSeek V3 (via OpenRouter)로 각 지역의 실제 환경 특성에 기반한 데이터를 생성하고,
기존 테스트에 사용되는 핵심 값은 보존한다.

Usage:
    python backend/scripts/enrich_demo_data.py
"""

import json
import os
import sys
import time
from pathlib import Path

# ── 프로젝트 루트 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── .env 로드 ──
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek/deepseek-chat")
DEMO_DIR = PROJECT_ROOT / "data" / "demo"
NOW = "2026-03-28T10:00:00+09:00"

# ── 14개 커넥터 전체 필드 스키마 ──
CONNECTOR_SCHEMAS = {
    "land_use": [
        "zone_type", "zone_conflict", "conservation_zone_overlap",
        "greenbelt_overlap", "military_zone_overlap", "agricultural_zone_overlap",
        "land_category", "land_area_m2", "restrictions",
        "forest_conservation_overlap",
    ],
    "ecology": [
        "eco_grade", "eco_grade_label", "endangered_species_distance_m",
        "endangered_species_list", "forest_wetland_distance_m", "forest_type",
        "natural_park_distance_m", "natural_park_name", "protected_area_overlap",
    ],
    "air_quality": [
        "station_name", "pm25_annual_avg", "pm10_annual_avg",
        "no2_annual_avg", "so2_annual_avg", "dust_source_distance_m",
        "regulated_zone", "air_quality_index",
    ],
    "water_quality": [
        "nearest_river", "river_distance_m", "water_source_protection_distance_m",
        "sensitive_water_zone", "sensitive_zone_name", "bod_avg", "tp_avg",
        "water_grade", "watershed",
    ],
    "noise": [
        "residential_distance_m", "quiet_facility_distance_m",
        "noise_level_leq_db", "noise_source_type", "vibration_level_db",
        "noise_countermeasure_zone", "vibration_sensitive_distance_m",
    ],
    "soil": [
        "contamination_risk", "groundwater_level_m", "soil_type",
        "organic_matter_pct", "ph_level", "landfill_distance_m",
        "geological_hazard_risk",
    ],
    "landscape": [
        "scenic_resource_distance_m", "viewpoint_impact",
        "landscape_grade", "light_pollution_sensitive",
        "landscape_conservation_zone",
    ],
    "cultural": [
        "heritage_protection_overlap", "buried_heritage_distance_m",
        "natural_monument_distance_m", "heritage_count_within_1km",
    ],
    "social": [
        "repeated_complaints", "similar_project_supplement_count",
    ],
    "population": [
        "population_density_per_km2", "residential_count_500m",
        "vulnerable_population_ratio", "relocation_households",
        "school_count_1km", "hospital_count_1km",
    ],
    "project_area": [
        "project_area_m2", "land_cover_type", "impervious_ratio",
        "vegetation_ratio", "elevation_avg_m", "slope_avg_deg",
    ],
    "eia_info": [
        "nearby_eia_count", "similar_project_eia_count",
        "common_mitigation_measures", "consultation_status", "last_eia_year",
    ],
    "marine": [
        "coastal_distance_m", "marine_protected_distance_m",
        "coastal_wetland_overlap", "fishery_zone_overlap",
        "fishery_zone_name", "tidal_flat_overlap", "beach_distance_m",
        "marine_species",
    ],
    "geology": [
        "terrain_type", "rock_type", "slope_grade", "steep_slope_risk",
        "subsidence_risk", "cut_fill_volume_m3", "elevation_range_m",
        "fault_distance_m",
    ],
    "greenhouse": [
        "estimated_annual_emission_tco2", "emission_trading_target",
        "carbon_neutral_zone", "regional_emission_intensity",
        "energy_efficiency_grade",
    ],
    "weather": [
        "avg_temp_c", "max_temp_c", "min_temp_c",
        "annual_precipitation_mm", "avg_wind_speed_ms",
        "dominant_wind_direction", "sunshine_hours", "fog_days",
        "frost_days", "station_name",
    ],
    "traffic": [
        "traffic_volume_daily", "road_type", "road_width_m",
        "school_route_distance_m", "traffic_impact_assessment_required",
        "public_transit_distance_m", "congestion_level",
        "nearby_intersection_count",
    ],
}

# ── 시나리오별 지역 특성 (DeepSeek 프롬프트용) ──
SCENARIO_CONTEXT = {
    "yangpyeong": {
        "description": "경기도 양평군 양평읍 — 남한강 수변, 농업지역+구릉지, 팔당상수원 수변구역",
        "project": "국도 우회도로 건설 (L=4.2km, 4차로)",
        "key_chars": "내륙 농업지역, 팔당상수원 수변구역, 생태자연도 2등급, 남한강 인접",
    },
    "sejong": {
        "description": "세종특별자치시 조치원읍 — 행복도시 인접 도시지역, 금강 수계",
        "project": "공동주택 건설 (12만㎡, 2,500세대)",
        "key_chars": "도시지역, 대기관리권역, 금강 인접, 신도시 개발",
    },
    "boryeong": {
        "description": "충청남도 보령시 주교면 — 서해안, 태안해안국립공원 인접, 보령댐 상류",
        "project": "LNG 복합화력발전소 (1,000MW)",
        "key_chars": "해안 인접, 생태자연도 1등급, 군사시설보호구역, 태안해안국립공원 근접, 습지보호지역",
    },
}


def _make_meta(tier: str, freshness: str = "live", fallback: bool = False) -> dict:
    """커넥터 메타데이터 생성."""
    return {
        "fetched_at": NOW,
        "snapshot_at": NOW if freshness == "live" else "2026-03-01T10:00:00+09:00",
        "freshness": freshness,
        "fallback_used": fallback,
        "tier": tier,
    }


def call_deepseek(prompt: str) -> str | None:
    """DeepSeek API 호출."""
    if not OPENROUTER_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": (
                    "당신은 한국 환경영향평가 전문가입니다. "
                    "주어진 지역의 환경 특성에 맞는 데이터를 JSON으로 생성합니다. "
                    "반드시 ```json ... ``` 블록으로 응답하세요."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"  DeepSeek 호출 실패: {e}")
        return None


def parse_json_response(text: str) -> dict | None:
    """LLM 응답에서 JSON 추출."""
    import re
    match = re.search(r"```json\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return None


def generate_missing_connectors(scenario: str, existing_connectors: dict) -> dict:
    """누락된 커넥터 데이터를 DeepSeek으로 생성한다."""
    missing = [name for name in CONNECTOR_SCHEMAS if name not in existing_connectors]
    if not missing:
        print(f"  {scenario}: all connectors present - skip")
        return {}

    ctx = SCENARIO_CONTEXT[scenario]
    fields_desc = ""
    for conn_name in missing:
        fields = CONNECTOR_SCHEMAS[conn_name]
        fields_desc += f"\n{conn_name}:\n  필드: {', '.join(fields)}\n"

    prompt = f"""다음 지역의 환경 데이터를 생성해 주세요.

## 지역 정보
- 위치: {ctx['description']}
- 사업: {ctx['project']}
- 특성: {ctx['key_chars']}

## 생성할 커넥터 데이터
{fields_desc}

## 규칙
- 한국의 실제 환경 데이터 범위에 맞는 현실적인 값을 사용하세요
- 숫자 값은 해당 지역의 실제 특성을 반영하세요
- null이 적절한 필드(예: 내륙 지역의 해양 데이터)는 null로 설정하세요
- 리스트 필드는 실제 한국 환경 용어를 사용하세요
- 모든 필드를 포함하는 하나의 JSON 객체로 응답하세요

## 출력 형식
```json
{{
  "connector_name": {{
    "field1": value1,
    "field2": value2
  }},
  ...
}}
```"""

    print(f"  {scenario}: {len(missing)}개 커넥터 생성 요청 ({', '.join(missing)})")
    text = call_deepseek(prompt)
    if not text:
        print(f"  {scenario}: DeepSeek 호출 실패 - 기본값 사용")
        return _generate_defaults(scenario, missing)

    parsed = parse_json_response(text)
    if not parsed:
        print(f"  {scenario}: JSON 파싱 실패 - 기본값 사용")
        return _generate_defaults(scenario, missing)

    print(f"  {scenario}: {len(parsed)}개 커넥터 데이터 생성 완료")
    return parsed


def _generate_defaults(scenario: str, missing: list[str]) -> dict:
    """DeepSeek 실패 시 기본 데이터."""
    defaults = {}
    ctx = SCENARIO_CONTEXT[scenario]
    is_coastal = "해안" in ctx["key_chars"]
    is_urban = "도시" in ctx["key_chars"]

    for name in missing:
        if name == "population":
            defaults[name] = {
                "population_density_per_km2": 3200 if is_urban else 450,
                "residential_count_500m": 120 if is_urban else 25,
                "vulnerable_population_ratio": 0.18 if is_urban else 0.12,
                "relocation_households": 0 if is_urban else 5,
                "school_count_1km": 3 if is_urban else 0,
                "hospital_count_1km": 2 if is_urban else 0,
            }
        elif name == "project_area":
            defaults[name] = {
                "project_area_m2": 120000 if is_urban else 85000,
                "land_cover_type": "시가화지역" if is_urban else "산림+농경지",
                "impervious_ratio": 0.45 if is_urban else 0.08,
                "vegetation_ratio": 0.15 if is_urban else 0.60,
                "elevation_avg_m": 50 if is_urban else 120,
                "slope_avg_deg": 3 if is_urban else 15,
            }
        elif name == "eia_info":
            defaults[name] = {
                "nearby_eia_count": 5 if is_urban else 2,
                "similar_project_eia_count": 12 if is_urban else 4,
                "common_mitigation_measures": ["방음벽 설치", "비점오염저감시설"],
                "consultation_status": "해당없음",
                "last_eia_year": 2024,
            }
        elif name == "marine":
            if is_coastal:
                defaults[name] = {
                    "coastal_distance_m": 2500,
                    "marine_protected_distance_m": 3800,
                    "coastal_wetland_overlap": False,
                    "fishery_zone_overlap": True,
                    "fishery_zone_name": "보령 연안어업 어장",
                    "tidal_flat_overlap": False,
                    "beach_distance_m": 5000,
                    "marine_species": ["꽃게", "바지락"],
                }
            else:
                defaults[name] = {
                    "coastal_distance_m": None,
                    "marine_protected_distance_m": None,
                    "coastal_wetland_overlap": None,
                    "fishery_zone_overlap": None,
                    "fishery_zone_name": None,
                    "tidal_flat_overlap": None,
                    "beach_distance_m": None,
                    "marine_species": None,
                }
        elif name == "geology":
            defaults[name] = {
                "terrain_type": "평탄지" if is_urban else "구릉지",
                "rock_type": "충적층" if is_urban else "편마암",
                "slope_grade": "완경사" if is_urban else "보통",
                "steep_slope_risk": False,
                "subsidence_risk": False,
                "cut_fill_volume_m3": 15000 if is_urban else 45000,
                "elevation_range_m": 15 if is_urban else 80,
                "fault_distance_m": 8000,
            }
        elif name == "greenhouse":
            is_power = "발전" in ctx["project"]
            defaults[name] = {
                "estimated_annual_emission_tco2": 2800000 if is_power else 8500,
                "emission_trading_target": is_power,
                "carbon_neutral_zone": False,
                "regional_emission_intensity": "높음" if is_power else "보통",
                "energy_efficiency_grade": None,
            }
        elif name == "weather":
            defaults[name] = {
                "avg_temp_c": 12.8 if is_coastal else 12.5,
                "max_temp_c": 35.8,
                "min_temp_c": -15.2,
                "annual_precipitation_mm": 1250 if is_coastal else 1180,
                "avg_wind_speed_ms": 3.2 if is_coastal else 2.1,
                "dominant_wind_direction": "북서" if is_coastal else "남서",
                "sunshine_hours": 2150,
                "fog_days": 35 if is_coastal else 20,
                "frost_days": 80,
                "station_name": scenario,
            }
        elif name == "traffic":
            defaults[name] = {
                "traffic_volume_daily": 45000 if is_urban else 8500,
                "road_type": "도시계획도로" if is_urban else "국도",
                "road_width_m": 25 if is_urban else 10,
                "school_route_distance_m": 200 if is_urban else 2000,
                "traffic_impact_assessment_required": is_urban,
                "public_transit_distance_m": 150 if is_urban else 1500,
                "congestion_level": "정체" if is_urban else "원활",
                "nearby_intersection_count": 5 if is_urban else 1,
            }

    return defaults


def enrich_existing_connectors(scenario: str, connectors: dict) -> dict:
    """기존 커넥터에 누락된 필드를 보충한다."""
    for conn_name, schema_fields in CONNECTOR_SCHEMAS.items():
        if conn_name not in connectors:
            continue
        conn = connectors[conn_name]
        for field in schema_fields:
            if field not in conn:
                conn[field] = None
    return connectors


def process_scenario(scenario: str) -> None:
    """단일 시나리오 처리."""
    mock_path = DEMO_DIR / scenario / "mock_data.json"
    if not mock_path.exists():
        print(f"  {scenario}: mock_data.json 없음 - 건너뜀")
        return

    data = json.loads(mock_path.read_text(encoding="utf-8"))
    connectors = data.get("connectors", {})

    # 1. legacy vworld 제거
    if "vworld" in connectors:
        del connectors["vworld"]
        print(f"  {scenario}: vworld 커넥터 제거")

    # 2. 누락 커넥터 생성 (DeepSeek 또는 기본값)
    missing_data = generate_missing_connectors(scenario, connectors)
    for conn_name, conn_data in missing_data.items():
        tier_map = {
            "land_use": "A", "air_quality": "A", "weather": "A",
            "ecology": "B", "water_quality": "B", "noise": "B",
            "soil": "B", "population": "B", "project_area": "B",
            "eia_info": "B", "marine": "B", "geology": "B",
            "traffic": "B",
            "landscape": "C", "cultural": "C", "social": "C",
            "greenhouse": "C",
        }
        tier = tier_map.get(conn_name, "C")
        merged = _make_meta(tier)
        merged.update(conn_data)
        connectors[conn_name] = merged

    # 3. 기존 커넥터 필드 보충
    connectors = enrich_existing_connectors(scenario, connectors)

    # 4. 기존 커넥터 메타데이터 갱신
    for conn_name, conn in connectors.items():
        conn["fetched_at"] = NOW
        if conn.get("freshness") == "live":
            conn["snapshot_at"] = NOW

    # 5. 최상위 메타 갱신
    data["fetched_at"] = NOW
    data["snapshot_at"] = NOW
    data["connectors"] = connectors

    # 6. 저장
    mock_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  {scenario}: 저장 완료 ({len(connectors)}개 커넥터)")


def main():
    print("=" * 60)
    print("데모 시나리오 실데이터 교체")
    print("=" * 60)

    for scenario in ["yangpyeong", "sejong", "boryeong"]:
        print(f"\n--- {scenario} ---")
        process_scenario(scenario)
        time.sleep(1)

    print("\n" + "=" * 60)
    print("완료. 리스크 엔진 검증 중...")
    print("=" * 60)

    # ── 리스크 엔진 재실행 검증 ──
    import asyncio
    os.environ["DEMO_MODE"] = "true"

    from backend.app.services.data_fetcher import DataFetcher
    from backend.app.services.risk_engine import RiskEngine

    COORDS = {
        "yangpyeong": (127.4875, 37.4913),
        "sejong": (127.0028, 36.6040),
        "boryeong": (126.5530, 36.3340),
    }

    engine = RiskEngine()
    engine.load_rules()
    fetcher = DataFetcher()

    async def validate():
        for scenario, (lng, lat) in COORDS.items():
            spatial = await fetcher.fetch_all_as_spatial_data(lng, lat, scenario=scenario)

            # project info 로드
            proj_path = DEMO_DIR / scenario / "mock_data.json"
            proj = json.loads(proj_path.read_text(encoding="utf-8")).get("project", {})

            risks = engine.evaluate(proj, spatial)
            criticals = [r for r in risks if r.severity == "critical"]
            majors = [r for r in risks if r.severity == "major"]
            reviews = [r for r in risks if r.severity == "review"]

            print(f"\n  {scenario}:")
            print(f"    총 리스크: {len(risks)}건")
            print(f"    Critical: {len(criticals)} — {[r.rule_id for r in criticals]}")
            print(f"    Major: {len(majors)} — {[r.rule_id for r in majors]}")
            print(f"    Review: {len(reviews)} — {[r.rule_id for r in reviews]}")

    asyncio.run(validate())
    print("\n검증 완료.")


if __name__ == "__main__":
    main()
