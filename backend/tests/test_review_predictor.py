"""검토의견 예측 + 품질 체크 테스트."""

import pytest

from backend.app.services.review_predictor import ReviewPredictor
from backend.app.services.quality_checker import QualityChecker


# ── ReviewPredictor ──


@pytest.fixture(scope="module")
def predictor() -> ReviewPredictor:
    return ReviewPredictor()


class TestReviewPredictor:
    """검토의견 예측 서비스 테스트."""

    def test_predict_road(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        assert result["project_type"] == "road"
        assert len(result["predicted_comments"]) > 0
        assert "disclaimer" in result

    def test_predict_housing(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="housing")
        assert result["project_type"] == "housing"
        assert len(result["predicted_comments"]) > 0

    def test_predict_power_plant(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="power_plant")
        assert result["project_type"] == "power_plant"
        assert len(result["predicted_comments"]) > 0

    def test_predict_factory(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="factory")
        assert result["project_type"] == "factory"

    def test_comments_sorted_by_probability(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        comments = result["predicted_comments"]
        probs = [c["probability_pct"] for c in comments]
        assert probs == sorted(probs, reverse=True)

    def test_risk_card_boosts_probability(self, predictor: ReviewPredictor) -> None:
        base = predictor.predict_review_comments(project_type="road")
        boosted = predictor.predict_review_comments(
            project_type="road",
            risk_cards=[
                {"title": "주거지역 인접 소음·진동", "severity": "major",
                 "rationale": "소음 영향 우려"},
            ],
        )
        # 소음 관련 항목은 리스크 매칭으로 확률이 높아져야 함
        base_noise = next(
            c for c in base["predicted_comments"] if c["category"] == "소음·진동"
        )
        boosted_noise = next(
            c for c in boosted["predicted_comments"] if c["category"] == "소음·진동"
        )
        assert boosted_noise["probability_pct"] > base_noise["probability_pct"]
        assert boosted_noise["risk_matched"] is True

    def test_severity_estimation(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        for comment in result["predicted_comments"]:
            if comment["probability_pct"] >= 70:
                assert comment["severity"] == "high"
            elif comment["probability_pct"] >= 40:
                assert comment["severity"] == "medium"
            else:
                assert comment["severity"] == "low"

    def test_total_past_cases(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        assert result["total_past_cases"] >= 0

    def test_has_korean_type(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        assert "korean_type" in result
        assert isinstance(result["korean_type"], str)

    def test_has_avg_review_months(self, predictor: ReviewPredictor) -> None:
        result = predictor.predict_review_comments(project_type="road")
        assert "avg_review_months" in result


# ── QualityChecker ──


@pytest.fixture(scope="module")
def checker() -> QualityChecker:
    return QualityChecker()


class TestQualityChecker:
    """품질 체크 서비스 테스트."""

    def test_check_empty(self, checker: QualityChecker) -> None:
        result = checker.check(project_type="road")
        assert "overall_status" in result
        assert "score" in result
        assert "checks" in result
        assert result["total_checks"] > 0

    def test_check_with_draft_sections(self, checker: QualityChecker) -> None:
        sections = [
            {"section_id": "ch1_s1", "title": "사업의 목적 및 필요성",
             "content": "본 사업은 양평 국도 우회도로 건설을 목적으로 하며 참고 자료입니다. " * 5},
            {"section_id": "ch3_s1", "title": "대기질",
             "content": "대기질 현황 조사 결과입니다. 실측 데이터 기반 분석 " * 5,
             "field_survey_required": True},
        ]
        result = checker.check(
            project_type="road",
            draft_sections=sections,
        )
        assert result["passed"] > 0

    def test_score_range(self, checker: QualityChecker) -> None:
        result = checker.check(project_type="road")
        assert 0 <= result["score"] <= 100

    def test_check_risk_mitigation(self, checker: QualityChecker) -> None:
        risk_cards = [
            {"rule_id": "ECO-001", "title": "생태자연도 1등급",
             "severity": "critical", "legal_basis": "자연환경보전법 제28조"},
        ]
        result = checker.check(
            project_type="road",
            risk_cards=risk_cards,
        )
        # 리스크 대응 체크가 포함되어야 함
        categories = {c["category"] for c in result["checks"]}
        assert "리스크 대응" in categories

    def test_check_legal_basis(self, checker: QualityChecker) -> None:
        risk_cards = [
            {"rule_id": "ECO-001", "title": "생태자연도 1등급",
             "severity": "critical", "legal_basis": "자연환경보전법 제28조"},
        ]
        result = checker.check(
            project_type="road",
            risk_cards=risk_cards,
        )
        categories = {c["category"] for c in result["checks"]}
        assert "데이터 품질" in categories

    def test_check_summary(self, checker: QualityChecker) -> None:
        result = checker.check(project_type="road")
        assert "summary" in result
        assert "필수 섹션" in result["summary"]
        assert "법적 요구사항" in result["summary"]

    def test_overall_status_values(self, checker: QualityChecker) -> None:
        result = checker.check(project_type="road")
        assert result["overall_status"] in ("pass", "warning", "fail")

    def test_disclaimer_check(self, checker: QualityChecker) -> None:
        sections = [
            {"section_id": "ch1_s1", "title": "테스트",
             "content": "이것은 참고 자료이며 전문가 검토가 필요합니다." * 5},
        ]
        result = checker.check(
            project_type="road",
            draft_sections=sections,
        )
        disc_checks = [c for c in result["checks"] if c["check_id"] == "DISC-001"]
        assert len(disc_checks) == 1
        assert disc_checks[0]["status"] == "pass"


# ── API 엔드포인트 ──


class TestReviewAPI:
    """Review API 엔드포인트 테스트."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    def test_predict_review_endpoint(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/predict-review",
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        assert "predicted_comments" in body
        assert len(body["predicted_comments"]) > 0
        assert "disclaimer" in body

    def test_predict_review_returns_project_type(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/predict-review",
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        assert "project_type" in body

    def test_quality_check_endpoint(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/quality-check",
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        assert "overall_status" in body
        assert "score" in body
        assert "checks" in body
        assert body["total_checks"] > 0

    def test_quality_check_status_values(self, client) -> None:
        r = client.post(
            "/api/screening/test-id/quality-check",
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["overall_status"] in ("pass", "warning", "fail")

    def test_openapi_has_review_endpoints(self, client) -> None:
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert "/api/screening/{screening_id}/predict-review" in paths
        assert "/api/screening/{screening_id}/quality-check" in paths
