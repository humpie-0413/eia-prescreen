"""Draft Copilot 테스트."""

import pytest

from backend.app.services.draft_copilot import DraftCopilot


@pytest.fixture(scope="module")
def copilot() -> DraftCopilot:
    return DraftCopilot()


# ── 템플릿 로드 ──


class TestTemplateLoad:
    """평가서 템플릿 로드 테스트."""

    def test_template_loaded(self, copilot: DraftCopilot) -> None:
        template = copilot.get_template()
        assert "chapters" in template
        assert len(template["chapters"]) == 7

    def test_template_has_sections(self, copilot: DraftCopilot) -> None:
        template = copilot.get_template()
        total_sections = sum(
            len(ch["sections"]) for ch in template["chapters"]
        )
        assert total_sections == 22

    def test_template_metadata(self, copilot: DraftCopilot) -> None:
        template = copilot.get_template()
        meta = template["metadata"]
        assert meta["total_chapters"] == 7
        assert meta["total_sections"] == 22


# ── 전체 초안 생성 ──


class TestFullDraft:
    """전체 초안 생성 테스트."""

    @pytest.mark.asyncio
    async def test_generates_all_sections(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={
                "project_name": "테스트 도로",
                "project_type": "road",
                "project_scale": "L=1km",
                "address": "서울시",
            },
        )
        assert "sections" in result
        assert result["total_sections"] == 22
        assert len(result["sections"]) == 22

    @pytest.mark.asyncio
    async def test_has_disclaimer(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        assert "AI가 생성한 참고 자료" in result["disclaimer"]

    @pytest.mark.asyncio
    async def test_has_generated_at(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        assert result["generated_at"] is not None

    @pytest.mark.asyncio
    async def test_sections_have_content(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={
                "project_name": "양평 도로",
                "project_type": "road",
                "address": "경기도 양평군",
            },
        )
        for section in result["sections"]:
            assert section["content"], f"Empty content for {section['section_id']}"
            assert section["title"]
            assert section["chapter"]

    @pytest.mark.asyncio
    async def test_badges_assigned(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        badges = {s["badge"] for s in result["sections"]}
        assert "자동 생성" in badges

    @pytest.mark.asyncio
    async def test_project_info_in_content(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_full_draft(
            project_info={
                "project_name": "세종 주거단지",
                "project_type": "housing",
                "address": "세종특별자치시",
            },
        )
        ch1_s1 = next(s for s in result["sections"] if s["section_id"] == "ch1_s1")
        assert "세종 주거단지" in ch1_s1["content"]
        assert "세종특별자치시" in ch1_s1["content"]


# ── 단일 섹션 생성 ──


class TestSingleSection:
    """단일 섹션 생성 테스트."""

    @pytest.mark.asyncio
    async def test_generate_ch1_s1(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch1_s1",
            project_info={
                "project_name": "보령 발전소",
                "project_type": "power_plant",
                "address": "충남 보령시",
            },
        )
        assert result is not None
        assert result["section_id"] == "ch1_s1"
        assert "보령 발전소" in result["content"]

    @pytest.mark.asyncio
    async def test_generate_ch1_s3_with_regulations(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch1_s3",
            project_info={"project_name": "테스트", "project_type": "road"},
            regulations=[
                {
                    "regulation_name": "농업진흥지역",
                    "legal_basis": "농지법 제32조",
                    "permit_required": True,
                    "related_authority": "농림부",
                },
            ],
        )
        assert result is not None
        assert "농업진흥지역" in result["content"]
        assert "농지법" in result["content"]

    @pytest.mark.asyncio
    async def test_generate_with_risk_cards(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch2_s1",
            project_info={"project_name": "테스트", "project_type": "road"},
            risk_cards=[
                {
                    "rule_id": "ECO-001",
                    "title": "생태자연도 1등급",
                    "severity": "critical",
                    "rationale": "1등급 중첩",
                    "legal_basis": "자연환경보전법",
                },
            ],
        )
        assert result is not None
        assert "생태자연도 1등급" in result["content"]

    @pytest.mark.asyncio
    async def test_invalid_section_returns_none(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="invalid_section",
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_field_survey_badge(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch3_s1",
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        assert result is not None
        assert result["badge"] == "현장조사 필요"
        assert result["field_survey_required"] is True

    @pytest.mark.asyncio
    async def test_expert_review_badge(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch6_s2",
            project_info={"project_name": "테스트", "project_type": "road"},
        )
        assert result is not None
        assert result["badge"] == "전문가 검토 필요"


# ── 패턴 연동 ──


class TestPatternIntegration:
    """과거 패턴 데이터 연동 테스트."""

    @pytest.mark.asyncio
    async def test_road_patterns_in_noise_section(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch3_s3",
            project_info={"project_name": "도로 사업", "project_type": "road"},
        )
        assert result is not None
        # 도로 사업의 소음 패턴이 포함되어야 함
        assert "소음" in result["content"]

    @pytest.mark.asyncio
    async def test_mitigation_section_has_patterns(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch4_s1",
            project_info={"project_name": "도로 사업", "project_type": "road"},
        )
        assert result is not None
        assert "저감" in result["content"]

    @pytest.mark.asyncio
    async def test_comprehensive_has_consultation_prediction(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch5_s1",
            project_info={"project_name": "도로 사업", "project_type": "road"},
        )
        assert result is not None
        assert "협의" in result["content"]

    @pytest.mark.asyncio
    async def test_conclusion_has_supplement_pct(self, copilot: DraftCopilot) -> None:
        result = await copilot.generate_section(
            section_id="ch5_s2",
            project_info={"project_name": "도로 사업", "project_type": "road"},
        )
        assert result is not None
        assert "보완" in result["content"]


# ── API 엔드포인트 ──


class TestDraftAPI:
    """Draft API 엔드포인트 테스트."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    def test_full_draft_endpoint(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft",
            json={"project_name": "양평 도로", "project_type": "road"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "sections" in body
        assert body["total_sections"] == 22
        assert "disclaimer" in body

    def test_section_draft_endpoint(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft/ch1_s1",
            json={"project_name": "양평 도로", "project_type": "road", "address": "경기도 양평군"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["section_id"] == "ch1_s1"
        assert "양평 도로" in body["content"]

    def test_section_not_found(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft/invalid_section",
            json={},
        )
        assert r.status_code == 404

    def test_template_endpoint(self, client) -> None:
        r = client.get("/api/draft/template")
        assert r.status_code == 200
        body = r.json()
        assert len(body["chapters"]) == 7

    def test_housing_draft(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft",
            json={"project_name": "세종 주거단지", "project_type": "housing", "address": "세종특별자치시"},
        )
        assert r.status_code == 200
        body = r.json()
        ch1_s1 = next(s for s in body["sections"] if s["section_id"] == "ch1_s1")
        assert "세종 주거단지" in ch1_s1["content"]

    def test_power_plant_draft(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft",
            json={"project_name": "보령 발전소", "project_type": "power_plant", "address": "충남 보령시"},
        )
        assert r.status_code == 200
        body = r.json()
        ch1_s1 = next(s for s in body["sections"] if s["section_id"] == "ch1_s1")
        assert "보령 발전소" in ch1_s1["content"]

    def test_custom_project_info(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/draft",
            json={
                "project_name": "커스텀 사업",
                "project_type": "housing",
            },
        )
        assert r.status_code == 200
        body = r.json()
        ch1_s1 = next(s for s in body["sections"] if s["section_id"] == "ch1_s1")
        assert "커스텀 사업" in ch1_s1["content"]

    def test_openapi_has_draft_endpoints(self, client) -> None:
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert "/api/screening/{screening_id}/draft" in paths
        assert "/api/screening/{screening_id}/draft/{section_id}" in paths
        assert "/api/draft/template" in paths
