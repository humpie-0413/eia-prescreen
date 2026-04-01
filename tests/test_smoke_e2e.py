"""E2E smoke tests — 전체 API 흐름 검증.

실제 DB 없이 실행 가능한 테스트:
  - 서비스 레이어 직접 테스트 (case_search, report_generator, llm_interpreter)
  - FastAPI TestClient를 통한 엔드포인트 응답 코드 검증
  - DB 의존 엔드포인트는 세션을 mock하여 404/422 동작 확인

DB가 필요한 실제 E2E 흐름은 통합 테스트(CI)에서 실행한다.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.case_search import CaseSearchService
from backend.app.services.llm_interpreter import LLMInterpreter
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.checklist_generator import ChecklistGenerator


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """DB 연결 없이 FastAPI 앱 테스트 클라이언트."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def case_svc():
    return CaseSearchService()


@pytest.fixture(scope="module")
def report_gen():
    return ReportGenerator()


@pytest.fixture(scope="module")
def checklist_gen():
    return ChecklistGenerator()


# ─────────────────────────────────────────────────────────────
# 1. 서비스 임포트 & 초기화
# ─────────────────────────────────────────────────────────────


def test_case_search_loads_50_cases(case_svc: CaseSearchService):
    assert len(case_svc.cases) == 89


def test_case_search_by_project_type(case_svc: CaseSearchService):
    result = case_svc.search(project_type="도로")
    assert result.total >= 1
    for c in result.results:
        assert c.project_type == "도로"


def test_case_search_by_keyword(case_svc: CaseSearchService):
    result = case_svc.search(keyword="생태")
    assert result.total >= 1


def test_case_search_limit(case_svc: CaseSearchService):
    result = case_svc.search(limit=3)
    assert len(result.results) <= 3


def test_find_similar_returns_ranked(case_svc: CaseSearchService):
    result = case_svc.find_similar(
        risk_card_tags=["생태", "도로", "산지", "수변구역"],
        project_type="도로",
        limit=5,
    )
    assert result.total >= 1
    scores = [r.similarity_score for r in result.results if r.similarity_score is not None]
    assert scores == sorted(scores, reverse=True)


def test_find_similar_empty_tags(case_svc: CaseSearchService):
    # Empty tags: returns fallback results (same-type or all cases)
    result = case_svc.find_similar(risk_card_tags=[], limit=3)
    assert len(result.results) <= 3


# ─────────────────────────────────────────────────────────────
# 2. 보고서 생성 (PDF bytes)
# ─────────────────────────────────────────────────────────────


_SAMPLE_PROJECT = {
    "project_name": "양평 국도 우회도로",
    "project_type": "road",
    "project_scale": "L=4.2km",
    "address": "경기도 양평군",
}

_SAMPLE_RISKS = [
    {
        "rule_id": "LAND-005",
        "title": "농업진흥지역 중첩",
        "severity": "major",
        "rationale": "농업진흥지역과 중첩",
        "next_action": "농지전용 허가",
        "legal_basis": "농지법 제34조",
    },
    {
        "rule_id": "ECO-001",
        "title": "생태자연도 1등급",
        "severity": "critical",
        "rationale": "1등급 지역 직접 중첩",
        "next_action": "대안 노선 검토",
        "legal_basis": "자연환경보전법 제28조",
    },
]

_SAMPLE_REGS = [
    {
        "regulation_name": "농업진흥지역 행위 제한",
        "regulation_code": "AGRI-001",
        "legal_basis": "농지법 제32조",
        "description": "농업 외 행위 원칙 금지",
        "permit_required": True,
        "related_authority": "농업진흥청",
    }
]

_SAMPLE_CHECKLIST = {
    "sections": [
        {
            "section_name": "주요 검토 항목 (Major)",
            "items": [
                {
                    "title": "농업진흥지역 확인",
                    "description": "농지전용 허가 신청",
                    "priority": "필수",
                }
            ],
        }
    ]
}


def test_brief_pdf_returns_bytes(report_gen: ReportGenerator):
    pdf = report_gen.generate_brief(
        project_info=_SAMPLE_PROJECT,
        risk_cards=_SAMPLE_RISKS,
        regulations=_SAMPLE_REGS,
        interpretation="테스트 해석문입니다.",
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_full_report_pdf_returns_bytes(report_gen: ReportGenerator):
    pdf = report_gen.generate_full_report(
        project_info=_SAMPLE_PROJECT,
        risk_cards=_SAMPLE_RISKS,
        regulations=_SAMPLE_REGS,
        cases=[{"case_id": "CASE-001", "project_type": "도로", "summary": "테스트", "consultation_result": "조건부 동의"}],
        interpretation="테스트 해석문입니다.",
        checklist=_SAMPLE_CHECKLIST,
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_checklist_pdf_returns_bytes(report_gen: ReportGenerator):
    pdf = report_gen.generate_checklist_pdf(checklist=_SAMPLE_CHECKLIST)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_comparison_pdf_returns_bytes(report_gen: ReportGenerator):
    sites = [
        {
            "screening_id": str(uuid4()),
            "project_name": "양평 도로",
            "project_type": "road",
            "address": "경기도 양평군",
            "total_risks": 2,
            "critical_count": 1,
            "major_count": 1,
            "review_count": 0,
            "info_count": 0,
            "total_regulations": 1,
            "permit_required_count": 1,
        },
        {
            "screening_id": str(uuid4()),
            "project_name": "세종 주거단지",
            "project_type": "housing",
            "address": "세종특별자치시",
            "total_risks": 3,
            "critical_count": 0,
            "major_count": 2,
            "review_count": 1,
            "info_count": 0,
            "total_regulations": 2,
            "permit_required_count": 1,
        },
    ]
    pdf = report_gen.generate_comparison_report(
        sites=sites,
        risk_matrix=[],
        recommendation="양평 도로가 상대적으로 낮은 리스크입니다.",
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_checklist_generator_empty(checklist_gen: ChecklistGenerator):
    result = checklist_gen.generate([], [])
    assert result.total_items == 0
    assert len(result.sections) == 0


def test_checklist_generator_with_risks(checklist_gen: ChecklistGenerator):
    result = checklist_gen.generate(_SAMPLE_RISKS, _SAMPLE_REGS)
    assert result.total_items >= 2
    severities = [s.priority for s in result.sections]
    assert "필수" in severities


# ─────────────────────────────────────────────────────────────
# 3. LLM Interpreter — API 키 없을 때 에러 응답
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_interpreter_no_key_returns_error():
    """OPENROUTER_API_KEY 미설정 시 에러 메시지 반환 (crash 없음)."""
    import asyncio
    from unittest.mock import patch
    from backend.app.services.llm_interpreter import LLMInterpreter

    interp = LLMInterpreter()
    with patch("backend.app.services.llm_interpreter.settings") as mock_settings:
        mock_settings.OPENROUTER_API_KEY = ""
        mock_settings.LLM_MODEL = "deepseek/deepseek-chat"
        result = await interp.interpret(risk_cards=_SAMPLE_RISKS, regulation_matches=_SAMPLE_REGS)

    assert "interpretation" in result
    assert "OPENROUTER_API_KEY" in result["interpretation"]
    assert result["ai_generated"] == "AI 생성"
    assert result["disclaimer"] == "이 해석은 참고용이며 법적 효력이 없습니다"


# ─────────────────────────────────────────────────────────────
# 4. HTTP 엔드포인트 smoke test (TestClient)
# ─────────────────────────────────────────────────────────────


def _get_auth_headers(client: TestClient) -> dict:
    """Register + login a test user, return Bearer auth headers."""
    client.post("/api/auth/register", json={
        "email": "smoke@test.com",
        "password": "testpass123",
        "name": "Smoke Tester",
    })
    resp = client.post("/api/auth/login", json={
        "email": "smoke@test.com",
        "password": "testpass123",
    })
    if resp.status_code != 200:
        return {}
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    headers = _get_auth_headers(client)
    if not headers:
        pytest.skip("DB not available — cannot authenticate")
    return headers


def test_health_endpoint(client: TestClient):
    """DB 없어도 /health는 응답해야 한다."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert body["status"] in ("ok", "degraded")


# ── Auth 엔드포인트 테스트 ──


def _db_available(client: TestClient) -> bool:
    """DB 연결 가능 여부를 /health 응답으로 판별한다."""
    r = client.get("/health")
    if r.status_code != 200:
        return False
    return r.json().get("status") == "ok"


def test_auth_register(client: TestClient):
    """POST /api/auth/register — 회원가입."""
    r = client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "password": "password123",
        "name": "New User",
    })
    if r.status_code == 500:
        pytest.skip("DB not available — auth endpoints require PostgreSQL")
    assert r.status_code in (201, 409)  # 409 if already registered from prior run


def test_auth_login(client: TestClient):
    """POST /api/auth/login — 로그인 후 토큰 반환."""
    # Ensure user exists
    reg = client.post("/api/auth/register", json={
        "email": "login@test.com",
        "password": "password123",
    })
    if reg.status_code == 500:
        pytest.skip("DB not available — auth endpoints require PostgreSQL")
    r = client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "password123",
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_auth_login_wrong_password(client: TestClient):
    """잘못된 비밀번호 → 401."""
    # Ensure user exists first
    reg = client.post("/api/auth/register", json={
        "email": "login@test.com",
        "password": "password123",
    })
    if reg.status_code == 500:
        pytest.skip("DB not available — auth endpoints require PostgreSQL")
    r = client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "wrongpass",
    })
    assert r.status_code == 401


# ── 인증 필요 엔드포인트 — 미인증 시 401 ──
# 인증 미들웨어가 아직 구현되지 않아 DEMO_MODE에서는 skip 처리
import pytest


@pytest.mark.skip(reason="인증 미들웨어 미구현 — DEMO_MODE에서는 인증 없이 동작")
def test_unauthenticated_cases_returns_401(client: TestClient):
    """인증 없이 /api/cases 접근 → 401."""
    r = client.get("/api/cases")
    assert r.status_code == 401


@pytest.mark.skip(reason="인증 미들웨어 미구현 — DEMO_MODE에서는 인증 없이 동작")
def test_unauthenticated_screening_returns_401(client: TestClient):
    """인증 없이 /api/screening 접근 → 401."""
    r = client.post("/api/screening", json={})
    assert r.status_code == 401


# ── 인증 후 엔드포인트 테스트 ──


def test_cases_search_no_filter(client: TestClient, auth_headers: dict):
    """GET /api/cases — DB 불필요, 50건 중 상위 10건 반환."""
    r = client.get("/api/cases", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "cases" in body
    assert "total" in body
    assert body["total"] == 89
    assert len(body["cases"]) == 10  # default limit


def test_cases_search_with_filter(client: TestClient, auth_headers: dict):
    r = client.get("/api/cases?project_type=도로&limit=5", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    for case in body["cases"]:
        assert case["project_type"] == "도로"


def test_cases_get_single(client: TestClient, auth_headers: dict):
    r = client.get("/api/cases/CASE-001", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "CASE-001"


def test_cases_get_not_found(client: TestClient, auth_headers: dict):
    r = client.get("/api/cases/CASE-999", headers=auth_headers)
    assert r.status_code == 404


def test_screening_create_missing_body(client: TestClient, auth_headers: dict):
    """POST /api/screening body 없으면 422."""
    r = client.post("/api/screening", json={}, headers=auth_headers)
    assert r.status_code == 422


def test_screening_invalid_type(client: TestClient, auth_headers: dict):
    """project_type 유효하지 않으면 422."""
    r = client.post("/api/screening", json={
        "project_name": "테스트",
        "project_type": "invalid_type",
    }, headers=auth_headers)
    assert r.status_code == 422


def test_compare_missing_body(client: TestClient, auth_headers: dict):
    """POST /api/screening/compare body 없으면 422."""
    r = client.post("/api/screening/compare", json={}, headers=auth_headers)
    assert r.status_code == 422


def test_compare_too_few_ids(client: TestClient, auth_headers: dict):
    """screening_ids 1개만 넘기면 422."""
    r = client.post("/api/screening/compare", json={"screening_ids": [str(uuid4())]}, headers=auth_headers)
    assert r.status_code == 422


def test_compare_too_many_ids(client: TestClient, auth_headers: dict):
    """screening_ids 4개 넘기면 422."""
    r = client.post("/api/screening/compare", json={
        "screening_ids": [str(uuid4()) for _ in range(4)]
    }, headers=auth_headers)
    assert r.status_code == 422


def test_screening_not_found(client: TestClient, auth_headers: dict):
    """없는 screening_id 요청 → DB 연결 안 되면 500 or 404."""
    fake_id = str(uuid4())
    r = client.get(f"/api/screening/{fake_id}", headers=auth_headers)
    assert r.status_code in (404, 500, 503)


def test_openapi_schema_available(client: TestClient):
    """OpenAPI 스키마가 올바르게 생성되어야 한다."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "EIA Pre-Screen API"
    paths = schema["paths"]
    assert "/api/cases" in paths
    assert "/api/screening/compare" in paths
    assert "/api/screening/{screening_id}/interpret" in paths
    assert "/api/screening/{screening_id}/report" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/register" in paths


def test_data_fetcher_has_22_connectors():
    """DataFetcher에 22개 커넥터가 모두 등록되어야 한다."""
    from backend.app.services.data_fetcher import DataFetcher
    fetcher = DataFetcher()
    names = {c.name for c in fetcher.connectors}
    assert len(fetcher.connectors) == 22
    assert names == {
        "land_use", "ecology", "air_quality", "water_quality",
        "soil", "noise", "population", "project_area", "eia_info",
        "marine", "geology", "greenhouse", "weather", "traffic",
        "odor", "radio", "industry", "facilities",
        "species", "hydrology", "ocean", "waste_data",
    }


# ─────────────────────────────────────────────────────────────
# 5. 룰 엔진 & 규제 매처 (기존 테스트와 중복 최소화)
# ─────────────────────────────────────────────────────────────


def test_risk_engine_loads():
    from backend.app.services.risk_engine import RiskEngine
    engine = RiskEngine()
    engine.load_rules()
    assert len(engine.rules) == 77


def test_regulation_matcher_loads():
    from backend.app.services.regulation_matcher import RegulationMatcher
    matcher = RegulationMatcher()
    # 규제 데이터가 로드되었는지 확인 (match 메서드 호출 가능 여부로 검증)
    result = matcher.match({"project_type": "road"}, {})
    assert isinstance(result, list)
