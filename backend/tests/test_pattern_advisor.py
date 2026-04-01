"""PatternAdvisor 서비스 테스트."""

import pytest
from backend.app.services.pattern_advisor import PatternAdvisor


@pytest.fixture
def advisor() -> PatternAdvisor:
    pa = PatternAdvisor()
    pa.load()
    return pa


class TestPatternAdvisorLoad:
    """데이터 로드 테스트."""

    def test_load_succeeds(self, advisor: PatternAdvisor) -> None:
        assert advisor._loaded is True

    def test_patterns_by_type_loaded(self, advisor: PatternAdvisor) -> None:
        assert "types" in advisor._patterns_by_type
        assert len(advisor._patterns_by_type["types"]) > 0

    def test_conslt_patterns_loaded(self, advisor: PatternAdvisor) -> None:
        summary = advisor._conslt_patterns.get("summary", {})
        assert summary.get("total_count", 0) > 0


class TestGetPatterns:
    """사업유형별 패턴 조회 테스트."""

    def test_road_patterns(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("road")
        assert result["project_type"] == "road"
        assert result["total_analyzed"] > 0
        assert len(result["type_data"]) > 0
        assert result["type_data"][0]["korean_type"] == "도로"

    def test_housing_patterns(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("housing")
        assert result["project_type"] == "housing"
        assert result["total_analyzed"] > 0

    def test_power_plant_patterns(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("power_plant")
        assert result["project_type"] == "power_plant"
        assert result["total_analyzed"] == 47

    def test_factory_patterns(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("factory")
        assert result["project_type"] == "factory"
        assert result["total_analyzed"] > 0

    def test_other_patterns_multiple_types(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("other")
        assert result["project_type"] == "other"
        assert len(result["type_data"]) > 1  # 여러 유형 합산

    def test_unknown_type_fallback(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("unknown_type")
        assert result["project_type"] == "unknown_type"
        # other로 폴백
        assert len(result["type_data"]) > 0

    def test_type_data_has_common_issues(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("road")
        td = result["type_data"][0]
        assert len(td["common_issues"]) > 0
        first = td["common_issues"][0]
        assert "issue" in first
        assert "count" in first
        assert "pct" in first

    def test_overall_total_set(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_patterns("road")
        assert result["overall_total"] > 0


class TestPredictIssues:
    """예상 지적항목 예측 테스트."""

    def test_road_prediction(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        assert result["project_type"] == "road"
        assert result["korean_type"] == "도로"
        assert len(result["predicted_issues"]) > 0

    def test_predicted_issue_fields(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        issue = result["predicted_issues"][0]
        assert "issue" in issue
        assert "probability_pct" in issue
        assert "past_count" in issue
        assert "description" in issue

    def test_consultation_prediction(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        cp = result["consultation_prediction"]
        assert "조건부협의" in cp
        assert cp["조건부협의"] > 0

    def test_remediation_suggestions(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        assert len(result["remediation_suggestions"]) > 0
        first = result["remediation_suggestions"][0]
        assert "issue" in first
        assert "common_remediation" in first
        assert len(first["common_remediation"]) > 0

    def test_with_location_type(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road", location_type="수변")
        assert result["risk_assessment"] is not None
        ra = result["risk_assessment"]
        assert ra["location_type"] == "수변"
        assert ra["risk_level"] in ("critical", "high", "major", "moderate", "low")
        assert 0 <= ra["issue_probability"] <= 1

    def test_without_location_type_no_risk_assessment(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        assert result["risk_assessment"] is None

    def test_invalid_location_type(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road", location_type="우주")
        assert result["risk_assessment"] is None

    def test_supplement_pct(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("road")
        assert result["supplement_required_pct"] is not None
        assert result["supplement_required_pct"] > 0

    def test_avg_review_months(self, advisor: PatternAdvisor) -> None:
        result = advisor.predict_issues("power_plant")
        assert result["avg_review_months"] is not None
        assert result["avg_review_months"] > 0


class TestGetSuggestedRules:
    """규칙 보강 제안 테스트."""

    def test_has_suggestions(self, advisor: PatternAdvisor) -> None:
        suggestions = advisor.get_suggested_rules()
        assert len(suggestions) > 0

    def test_suggestion_fields(self, advisor: PatternAdvisor) -> None:
        suggestions = advisor.get_suggested_rules()
        s = suggestions[0]
        assert "suggestion_id" in s
        assert "title" in s
        assert "issue" in s
        assert "evidence" in s
        assert "recommended_severity" in s
        assert s["recommended_severity"] in ("critical", "major", "review", "info")

    def test_suggestion_ids_unique(self, advisor: PatternAdvisor) -> None:
        suggestions = advisor.get_suggested_rules()
        ids = [s["suggestion_id"] for s in suggestions]
        assert len(ids) == len(set(ids))


class TestGetOverallSummary:
    """전체 요약 테스트."""

    def test_summary(self, advisor: PatternAdvisor) -> None:
        result = advisor.get_overall_summary()
        assert result["total_count"] > 0
        assert result["year_range"] != ""
        assert len(result["biz_type_distribution"]) > 0
        assert len(result["available_types"]) > 0
