"""Medium-depth tests targeting connector retry/fallback, severity-specific rules,
regulation matching, LLM interpreter, PDF generation, Prometheus metrics, and config defaults.

20+ tests across 7 functional areas.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio  # noqa: F401

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataFreshness,
    DataTier,
)
from backend.app.core.config import Settings
from backend.app.services.llm_interpreter import LLMInterpreter
from backend.app.services.regulation_matcher import RegulationMatcher
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.risk_engine import RiskEngine


# ═══════════════════════════════════════════════════════════════
# 1. Connector retry / fallback tests
# ═══════════════════════════════════════════════════════════════


class _DummyConnector(BaseConnector):
    """Concrete subclass of BaseConnector for testing fetch_with_retry."""

    name = "dummy"
    tier = DataTier.B
    description = "test connector"

    def __init__(self, side_effects):
        self._side_effects = iter(side_effects)

    async def fetch(self, lng, lat, buffer_m=1000, **kwargs):
        effect = next(self._side_effects)
        if isinstance(effect, Exception):
            raise effect
        return effect

    async def fetch_demo(self, scenario):
        return self._make_result({})


def _stable_result(name="dummy") -> ConnectorResult:
    return ConnectorResult(
        connector_name=name,
        tier="B",
        status=ConnectorStatus.STABLE,
        freshness=DataFreshness(freshness="live"),
        data={"ok": True},
    )


def _unavailable_result(name="dummy") -> ConnectorResult:
    return ConnectorResult(
        connector_name=name,
        tier="B",
        status=ConnectorStatus.UNAVAILABLE,
        freshness=DataFreshness(freshness="unknown"),
        data=None,
        error="service unavailable",
    )


@pytest.mark.asyncio
async def test_fetch_with_retry_succeeds_first_try():
    """fetch_with_retry should return immediately when fetch succeeds on the first attempt."""
    conn = _DummyConnector([_stable_result()])
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await conn.fetch_with_retry(127.0, 37.0)
    assert result.status == ConnectorStatus.STABLE
    assert result.data == {"ok": True}


@pytest.mark.asyncio
async def test_fetch_with_retry_succeeds_second_attempt():
    """fetch_with_retry should succeed on the second attempt after a first-try exception."""
    conn = _DummyConnector([RuntimeError("transient"), _stable_result()])
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await conn.fetch_with_retry(127.0, 37.0)
    assert result.status == ConnectorStatus.STABLE
    mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_with_retry_all_attempts_fail():
    """fetch_with_retry should return error ConnectorResult after all attempts fail."""
    conn = _DummyConnector([
        RuntimeError("fail1"),
        RuntimeError("fail2"),
        RuntimeError("fail3"),
    ])
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await conn.fetch_with_retry(127.0, 37.0, max_attempts=3)
    assert result.status == ConnectorStatus.UNAVAILABLE
    assert result.error is not None
    assert "All 3 attempts failed" in result.error


@pytest.mark.asyncio
async def test_fetch_with_retry_retries_on_unavailable():
    """fetch_with_retry should retry when fetch returns UNAVAILABLE status, then succeed."""
    conn = _DummyConnector([_unavailable_result(), _stable_result()])
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await conn.fetch_with_retry(127.0, 37.0)
    assert result.status == ConnectorStatus.STABLE
    assert result.data == {"ok": True}
    mock_sleep.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════
# 2. Severity-specific rule engine tests
# ═══════════════════════════════════════════════════════════════


_PROJECT_INFOS = {
    "yangpyeong": {"project_name": "양평 국도 우회도로", "project_type": "road"},
    "sejong": {"project_name": "세종 행복도시 3-2생활권", "project_type": "housing"},
    "boryeong": {"project_name": "보령 복합화력발전소", "project_type": "power_plant"},
}

_SPATIAL_DATA = {
    "yangpyeong": {
        "land_use": {"agricultural_zone_overlap": True, "zone_conflict": False, "conservation_zone_overlap": False, "greenbelt_overlap": False, "military_zone_overlap": False, "forest_conservation_overlap": False, "river_zone_overlap": False, "road_buffer_zone_overlap": False},
        "ecology": {"eco_grade": 2, "endangered_species_distance_m": 800, "forest_wetland_distance_m": 300, "natural_park_distance_m": 2500, "baekdudaegan_distance_m": 15000, "eco_landscape_conservation_overlap": False, "eco_corridor_distance_m": 500},
        "water": {"river_distance_m": 80, "water_source_protection_distance_m": 5000, "sensitive_water_zone": True, "total_pollution_load_area": False, "underground_water_protection_distance_m": 500},
        "air_quality": {"pm25_annual_avg": 22.5, "dust_source_distance_m": 5000, "regulated_zone": False, "pm10_annual_avg": 42, "odor_management_zone": False},
        "noise": {"residential_distance_m": 250, "quiet_facility_distance_m": 350, "noise_countermeasure_zone": False, "vibration_sensitive_distance_m": 300},
        "soil": {"contamination_risk": False, "groundwater_level_m": 5, "landfill_distance_m": 3000, "geological_hazard_risk": False},
        "cultural": {"heritage_protection_overlap": False, "buried_heritage_distance_m": 500, "natural_monument_distance_m": 2000},
        "landscape": {"scenic_resource_distance_m": 800, "viewpoint_impact": False, "light_pollution_sensitive": False},
        "social": {"repeated_complaints": 1, "similar_project_supplement_count": 1, "environmental_justice_vulnerable": False},
    },
    "boryeong": {
        "land_use": {"zone_conflict": True, "conservation_zone_overlap": False, "greenbelt_overlap": False, "military_zone_overlap": True, "agricultural_zone_overlap": True, "forest_conservation_overlap": True, "river_zone_overlap": True, "road_buffer_zone_overlap": True},
        "ecology": {"eco_grade": 1, "endangered_species_distance_m": 500, "forest_wetland_distance_m": 200, "natural_park_distance_m": 800, "baekdudaegan_distance_m": 5000, "eco_landscape_conservation_overlap": False, "eco_corridor_distance_m": 150},
        "water": {"river_distance_m": 50, "water_source_protection_distance_m": 450, "sensitive_water_zone": True, "total_pollution_load_area": True, "underground_water_protection_distance_m": 200},
        "air_quality": {"pm25_annual_avg": 38.2, "dust_source_distance_m": 1500, "regulated_zone": True, "pm10_annual_avg": 55, "odor_management_zone": False},
        "noise": {"residential_distance_m": 120, "quiet_facility_distance_m": 180, "noise_countermeasure_zone": False, "vibration_sensitive_distance_m": 80},
        "soil": {"contamination_risk": True, "groundwater_level_m": 2.5, "landfill_distance_m": 350, "geological_hazard_risk": True},
        "cultural": {"heritage_protection_overlap": False, "buried_heritage_distance_m": 150, "natural_monument_distance_m": 800},
        "landscape": {"scenic_resource_distance_m": 300, "viewpoint_impact": True, "light_pollution_sensitive": True},
        "social": {"repeated_complaints": 5, "similar_project_supplement_count": 3, "environmental_justice_vulnerable": True},
    },
}


@pytest.fixture(scope="module")
def engine():
    e = RiskEngine()
    e.load_rules()
    return e


@pytest.fixture(scope="module")
def _all_eval(engine):
    """Pre-compute evaluation results using inline spatial data fixtures."""
    out = {}
    for scenario in ("yangpyeong", "boryeong"):
        project_info = _PROJECT_INFOS[scenario]
        spatial = _SPATIAL_DATA[scenario]
        risks = engine.evaluate(project_info, spatial)
        out[scenario] = risks
    return out


def test_critical_severity_only_boryeong(_all_eval):
    """Boryeong should have exactly {ECO-001, LAND-001, LAND-006, WAT-002} as critical rules."""
    risks = _all_eval["boryeong"]
    critical_ids = {r.rule_id for r in risks if r.severity == "critical"}
    assert critical_ids == {"ECO-001", "LAND-001", "LAND-006", "WAT-002"}


def test_major_severity_count_yangpyeong(_all_eval):
    """Yangpyeong should have at least 4 major-severity risks."""
    risks = _all_eval["yangpyeong"]
    major_count = sum(1 for r in risks if r.severity == "major")
    assert major_count >= 4, f"Expected >= 4 major risks, got {major_count}"


def test_review_severity_exists_yangpyeong(_all_eval):
    """Yangpyeong should have at least 1 review-level risk."""
    risks = _all_eval["yangpyeong"]
    review_count = sum(1 for r in risks if r.severity == "review")
    assert review_count >= 1, "Expected at least 1 review-level risk in yangpyeong"


def test_info_severity_exists_boryeong(_all_eval):
    """Boryeong should have at least 1 info-level risk."""
    risks = _all_eval["boryeong"]
    info_count = sum(1 for r in risks if r.severity == "info")
    assert info_count >= 1, "Expected at least 1 info-level risk in boryeong"


# ═══════════════════════════════════════════════════════════════
# 3. Regulation matcher tests
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def matcher():
    return RegulationMatcher()


def test_matcher_returns_list(matcher):
    """match() with a project_type should return a list."""
    result = matcher.match({"project_type": "power_plant"}, {})
    assert isinstance(result, list)


def test_matcher_eco_grade_1(matcher):
    """Spatial data with eco_grade=1 should produce a regulation containing '생태자연도'."""
    spatial_data = {"ecology": {"eco_grade": 1}}
    result = matcher.match({"project_type": "power_plant"}, spatial_data)
    eco_names = [r.regulation_name for r in result if "생태자연도" in r.regulation_name]
    assert len(eco_names) >= 1, f"Expected eco-grade regulation, got names: {[r.regulation_name for r in result]}"


def test_matcher_military_zone(matcher):
    """Spatial data with military_zone_overlap=true should match a regulation with '군사'."""
    spatial_data = {"land_use": {"military_zone_overlap": True}}
    result = matcher.match({"project_type": "road"}, spatial_data)
    mil_names = [r.regulation_name for r in result if "군사" in r.regulation_name]
    assert len(mil_names) >= 1, f"Expected military regulation, got names: {[r.regulation_name for r in result]}"


# ═══════════════════════════════════════════════════════════════
# 4. LLM interpreter tests
# ═══════════════════════════════════════════════════════════════

_RISK_CARDS = [
    {"rule_id": "ECO-001", "title": "생태자연도 1등급", "severity": "critical", "rationale": "1등급 중첩"},
    {"rule_id": "WAT-002", "title": "상수원보호 인접", "severity": "critical", "rationale": "500m 이내"},
]

_REG_MATCHES = [
    {"regulation_name": "생태자연도 1등급 보전", "regulation_code": "eco_grade_1", "legal_basis": "자연환경보전법"},
]


def test_llm_prompt_contains_risks():
    """_build_prompt should include rule_id and title from each risk card."""
    interp = LLMInterpreter()
    prompt = interp._build_prompt(_RISK_CARDS, _REG_MATCHES)
    assert "ECO-001" in prompt
    assert "생태자연도 1등급" in prompt
    assert "WAT-002" in prompt
    assert "상수원보호 인접" in prompt


def test_llm_error_response_structure():
    """_error_response should return a dict with all required keys."""
    interp = LLMInterpreter()
    resp = interp._error_response("test error")
    assert "interpretation" in resp
    assert "model" in resp
    assert "generated_at" in resp
    assert "disclaimer" in resp
    assert "ai_generated" in resp
    assert resp["interpretation"] == "test error"
    assert resp["ai_generated"] == "AI 생성"


@pytest.mark.asyncio
async def test_llm_interpret_with_mock_api():
    """interpret() should return interpretation text when the API is mocked."""
    interp = LLMInterpreter()

    # Build a mock response that mimics the OpenAI chat completion structure
    mock_message = MagicMock()
    mock_message.content = "이 사업은 환경적으로 높은 리스크를 가지고 있습니다."

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(return_value=mock_response)

    mock_chat = MagicMock()
    mock_chat.completions = mock_completions

    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("backend.app.services.llm_interpreter.settings") as mock_settings, \
         patch("backend.app.services.llm_interpreter.AsyncOpenAI", return_value=mock_client):
        mock_settings.OPENROUTER_API_KEY = "test-key-123"
        mock_settings.LLM_MODEL = "deepseek/deepseek-chat"
        result = await interp.interpret(risk_cards=_RISK_CARDS, regulation_matches=_REG_MATCHES)

    assert result["interpretation"] == "이 사업은 환경적으로 높은 리스크를 가지고 있습니다."
    assert result["ai_generated"] == "AI 생성"
    assert "disclaimer" in result


# ═══════════════════════════════════════════════════════════════
# 5. PDF generation tests
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def report_gen():
    return ReportGenerator()


_PDF_PROJECT = {
    "project_name": "테스트 프로젝트",
    "project_type": "power_plant",
    "project_scale": "500MW",
    "address": "충청남도 보령시",
}

_PDF_RISKS = [
    {"rule_id": "ECO-001", "title": "생태자연도 1등급", "severity": "높음",
     "rationale": "1등급 중첩", "next_action": "대안 검토", "legal_basis": "자연환경보전법"},
    {"rule_id": "WAT-002", "title": "상수원보호 인접", "severity": "높음",
     "rationale": "500m 이내", "next_action": "오염방지계획", "legal_basis": "수도법"},
    {"rule_id": "NOI-001", "title": "주거지 소음", "severity": "중간",
     "rationale": "250m 이내", "next_action": "방음벽", "legal_basis": "소음진동법"},
]

_PDF_REGS = [
    {"regulation_name": "생태자연도 1등급", "legal_basis": "자연환경보전법", "permit_required": True, "related_authority": "환경부"},
    {"regulation_name": "상수원보호구역", "legal_basis": "수도법", "permit_required": True, "related_authority": "환경부"},
]

_PDF_CHECKLIST = {
    "sections": [
        {
            "section_name": "즉시 확인 필요 (Critical)",
            "items": [
                {"title": "생태 현황 조사", "description": "1등급 지역 현장 확인", "priority": "높음"},
                {"title": "수질 영향 조사", "description": "상수원 인접 수질 모니터링", "priority": "높음"},
            ],
        },
        {
            "section_name": "주요 검토 항목 (Major)",
            "items": [
                {"title": "소음 측정", "description": "주거지 인접 소음 레벨 측정", "priority": "중간"},
            ],
        },
    ]
}


def test_brief_pdf_size(report_gen):
    """Brief PDF should be larger than 1000 bytes."""
    pdf = report_gen.generate_brief(
        project_info=_PDF_PROJECT,
        risk_cards=_PDF_RISKS,
        regulations=_PDF_REGS,
        interpretation="테스트 해석문: 이 사업은 리스크가 높습니다.",
    )
    assert len(pdf) > 1000, f"Brief PDF too small: {len(pdf)} bytes"


def test_full_report_includes_all_sections(report_gen):
    """Full report with 3 risks should be larger than 5000 bytes."""
    pdf = report_gen.generate_full_report(
        project_info=_PDF_PROJECT,
        risk_cards=_PDF_RISKS,
        regulations=_PDF_REGS,
        cases=[{"case_id": "CASE-001", "project_type": "발전소", "summary": "요약", "consultation_result": "동의"}],
        interpretation="종합 해석: 리스크 분석 결과 높은 환경 위험이 확인됩니다.",
        checklist=_PDF_CHECKLIST,
    )
    assert len(pdf) > 5000, f"Full report too small: {len(pdf)} bytes"


def test_checklist_pdf_structure(report_gen):
    """Checklist PDF should start with %PDF header."""
    pdf = report_gen.generate_checklist_pdf(checklist=_PDF_CHECKLIST)
    assert pdf[:4] == b"%PDF", f"Unexpected PDF header: {pdf[:10]}"


def test_comparison_pdf_multiple_sites(report_gen):
    """Comparison report with 3 sites should produce valid PDF bytes."""
    sites = [
        {
            "screening_id": str(uuid4()),
            "project_name": f"부지 {i+1}",
            "project_type": "power_plant",
            "address": f"주소 {i+1}",
            "total_risks": 5 + i,
            "critical_count": i,
            "major_count": 2,
            "review_count": 1,
            "info_count": 2 + i,
            "total_regulations": 3,
            "permit_required_count": 2,
        }
        for i in range(3)
    ]
    pdf = report_gen.generate_comparison_report(
        sites=sites,
        risk_matrix=[
            {
                "rule_id": "ECO-001",
                "title": "생태자연도 1등급",
                "severity_by_site": {
                    sites[0]["screening_id"]: "critical",
                    sites[1]["screening_id"]: "major",
                    sites[2]["screening_id"]: None,
                },
            }
        ],
        recommendation="부지 3이 환경적으로 가장 적합합니다.",
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


# ═══════════════════════════════════════════════════════════════
# 6. Metrics module tests
# ═══════════════════════════════════════════════════════════════


def test_metrics_endpoint_returns_prometheus():
    """GET /metrics should return a response with Prometheus-compatible content type."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus content type is either text/plain or openmetrics-text
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct or "openmetrics" in ct, f"Unexpected content-type: {ct}"


def test_request_counter_increments():
    """REQUEST_COUNT counter should increment when labels are applied."""
    from backend.app.core.metrics import REQUEST_COUNT

    label = REQUEST_COUNT.labels(method="GET", endpoint="/test-counter", status_code=200)
    before = label._value.get()
    label.inc()
    after = label._value.get()
    assert after == before + 1


def test_connector_counter_increments():
    """CONNECTOR_REQUESTS counter should increment when labels are applied."""
    from backend.app.core.metrics import CONNECTOR_REQUESTS

    label = CONNECTOR_REQUESTS.labels(connector="test_connector", status="success")
    before = label._value.get()
    label.inc()
    after = label._value.get()
    assert after == before + 1


# ═══════════════════════════════════════════════════════════════
# 7. Config tests
# ═══════════════════════════════════════════════════════════════


def test_default_environment():
    """Default ENVIRONMENT should be 'development'."""
    s = Settings()
    assert s.ENVIRONMENT == "development"


def test_default_log_level():
    """Default LOG_LEVEL should be 'INFO'."""
    s = Settings()
    assert s.LOG_LEVEL == "INFO"
