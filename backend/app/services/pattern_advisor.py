"""과거 환경영향평가 패턴 기반 자문 서비스.

수집된 과거 환평 데이터(9,973건)의 분석 결과를 로드하여
사업유형별 패턴 조회, 예상 지적항목, 리스크 확률을 제공한다.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ANALYSIS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "bulk" / "analysis"

# 사업유형 매핑: ProjectType enum → 한국어 사업유형 (환경영향평가법 시행령 별표3 기준 17개)
_TYPE_MAP: dict[str, list[str]] = {
    "urban_dev": ["도시계획", "도시개발", "택지개발", "대지조성"],
    "industrial": ["산업단지", "산업입지", "농공단지"],
    "energy": ["발전소", "화력", "원자력", "태양광", "풍력"],
    "port": ["항만", "어항", "마리나"],
    "road": ["도로", "국도", "고속도로"],
    "water_resource": ["댐", "저수지", "하구둑", "용수"],
    "railway": ["철도", "고속철도", "도시철도", "경전철"],
    "airport": ["공항", "활주로", "비행장"],
    "river": ["하천", "하천공사", "하천정비"],
    "tourism": ["관광단지", "관광", "리조트", "골프장", "테마파크"],
    "mountain": ["채석", "광업", "산지전용", "석산"],
    "sports": ["체육", "스키장", "경기장", "골프"],
    "waste": ["폐기물", "소각", "분뇨"],
    "military": ["군사", "국방", "사격장", "훈련장"],
    "mining": ["토석", "골재", "광물", "채굴"],
    "reclamation": ["간척", "매립간척", "공유수면"],
    "etc": ["물류", "유통", "교육", "의료", "상하수도"],
    # 이전 호환
    "power_plant": ["발전소"], "factory": ["산업단지"],
    "housing": ["주거단지"],
    "other": ["하천", "도시계획", "관광단지", "공원", "항만", "기타"],
}

# 역방향 매핑: 한국어 → ProjectType
_REVERSE_TYPE_MAP: dict[str, str] = {}
for eng, kr_list in _TYPE_MAP.items():
    for kr in kr_list:
        _REVERSE_TYPE_MAP[kr] = eng


def _load_json(filename: str) -> dict:
    """분석 JSON 파일을 로드한다."""
    path = _ANALYSIS_DIR / filename
    if not path.exists():
        logger.warning("분석 파일 없음: %s", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("분석 파일 로드 실패: %s — %s", path, e)
        return {}


class PatternAdvisor:
    """과거 환평 패턴 자문 서비스."""

    def __init__(self) -> None:
        self._patterns_by_type: dict = {}
        self._risk_matrix: dict = {}
        self._common_issues: dict = {}
        self._remediation_patterns: dict = {}
        self._conslt_patterns: dict = {}
        self._loaded = False

    def load(self) -> None:
        """분석 데이터를 로드한다."""
        self._patterns_by_type = _load_json("patterns_by_type.json")
        self._risk_matrix = _load_json("risk_matrix.json")
        self._common_issues = _load_json("common_issues.json")
        self._remediation_patterns = _load_json("remediation_patterns.json")
        self._conslt_patterns = _load_json("conslt_patterns.json")
        self._loaded = True

        type_count = len(self._patterns_by_type.get("types", {}))
        total = self._conslt_patterns.get("summary", {}).get("total_count", 0)
        logger.info("PatternAdvisor 로드 완료: %d개 유형, 총 %d건", type_count, total)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _resolve_kr_types(self, project_type: str) -> list[str]:
        """ProjectType을 한국어 사업유형 목록으로 변환."""
        return _TYPE_MAP.get(project_type, _TYPE_MAP["other"])

    def get_patterns(self, project_type: str) -> dict[str, Any]:
        """사업유형별 과거 패턴 조회.

        Returns:
            {
                "project_type": str,
                "total_analyzed": int,
                "type_data": [...],  # 매칭된 한국어 유형별 상세
                "consultation_summary": {...},
                "overall_summary": {...},
            }
        """
        self._ensure_loaded()

        types = self._patterns_by_type.get("types", {})
        kr_types = self._resolve_kr_types(project_type)

        type_data = []
        total_count = 0

        for kr in kr_types:
            if kr in types:
                entry = types[kr]
                type_data.append({
                    "korean_type": kr,
                    "total_count": entry["total_count"],
                    "consultation_results": entry.get("consultation_results", {}),
                    "result_pct": entry.get("result_pct", {}),
                    "common_issues": entry.get("common_issues", []),
                    "avg_review_months": entry.get("avg_review_months"),
                    "supplement_required_pct": entry.get("supplement_required_pct"),
                })
                total_count += entry["total_count"]

        # 전체 통계
        summary = self._conslt_patterns.get("summary", {})

        return {
            "project_type": project_type,
            "total_analyzed": total_count,
            "overall_total": summary.get("total_count", 0),
            "analysis_year_range": summary.get("year_range", ""),
            "type_data": type_data,
        }

    def predict_issues(self, project_type: str, location_type: str | None = None) -> dict[str, Any]:
        """예상 지적항목 + 확률 예측.

        Args:
            project_type: 사업유형 (road, housing, power_plant, factory, other)
            location_type: 입지유형 (산지, 수변, 농지, 도시, 해안, 평지) — 선택

        Returns:
            {
                "project_type": str,
                "predicted_issues": [...],
                "consultation_prediction": {...},
                "risk_assessment": {...},  # location_type이 있을 때
                "remediation_suggestions": [...],
            }
        """
        self._ensure_loaded()

        types = self._patterns_by_type.get("types", {})
        kr_types = self._resolve_kr_types(project_type)

        # 가장 구체적인 매칭 (첫 번째 유형 사용)
        primary_kr = kr_types[0] if kr_types else "기타"
        type_entry = types.get(primary_kr, {})

        # 예상 지적항목
        common_issues = type_entry.get("common_issues", [])
        predicted_issues = [
            {
                "issue": item["issue"],
                "probability_pct": item["pct"],
                "past_count": item["count"],
                "total_in_type": type_entry.get("total_count", 0),
                "description": f"과거 {primary_kr} 사업 {type_entry.get('total_count', 0)}건 중 "
                               f"{item['count']}건({item['pct']}%)에서 지적",
            }
            for item in common_issues
        ]

        # 협의결과 예측
        result_pct = type_entry.get("result_pct", {})
        consultation_prediction = {
            "조건부협의": result_pct.get("조건부협의", 0),
            "협의": result_pct.get("협의", 0),
            "재검토": result_pct.get("재검토", 0),
            "기타": result_pct.get("기타", 0),
        }

        # 입지 리스크 매트릭스
        risk_assessment = None
        if location_type:
            matrix = self._risk_matrix.get("matrix", {})
            type_matrix = matrix.get(primary_kr, {})
            loc_risk = type_matrix.get(location_type)
            if loc_risk:
                risk_assessment = {
                    "location_type": location_type,
                    "risk_level": loc_risk["risk_level"],
                    "issue_probability": loc_risk["issue_probability"],
                    "top_issues": loc_risk["top_issues"],
                    "supplement_probability_pct": loc_risk["supplement_pct"],
                }

        # 보완 패턴
        remediation_data = self._remediation_patterns.get("by_type", {})
        type_remediation = remediation_data.get(primary_kr, [])
        remediation_suggestions = [
            {
                "issue": item["issue"],
                "common_remediation": item["common_remediation"],
                "frequency": item["frequency"],
            }
            for item in type_remediation
        ]

        return {
            "project_type": project_type,
            "korean_type": primary_kr,
            "total_in_type": type_entry.get("total_count", 0),
            "predicted_issues": predicted_issues,
            "consultation_prediction": consultation_prediction,
            "avg_review_months": type_entry.get("avg_review_months"),
            "supplement_required_pct": type_entry.get("supplement_required_pct"),
            "risk_assessment": risk_assessment,
            "remediation_suggestions": remediation_suggestions,
        }

    def get_suggested_rules(self, existing_rule_domains: list[str] | None = None) -> list[dict[str, Any]]:
        """기존 규칙에 없는 패턴에서 신규 규칙 제안.

        과거 데이터에서 빈번하게 지적되지만 현재 64개 규칙에 누락된 항목을 제안한다.
        """
        self._ensure_loaded()

        # 기존 규칙에 이미 커버되는 도메인 키워드
        covered_keywords = {
            "소음", "진동", "대기", "수질", "생태", "경관",
            "농지", "산지", "토양", "교통", "해양", "온실가스",
            "지형", "문화재", "폐기물",
        }

        if existing_rule_domains:
            covered_keywords.update(existing_rule_domains)

        # 전체 이슈에서 기존 규칙에 매핑되지 않는 항목 찾기
        overall = self._common_issues.get("overall_top_10", [])

        suggestions = []
        suggestion_id = 1

        # 사업유형별 고유 이슈 탐색 (patterns_by_type의 top 10 사용)
        types = self._patterns_by_type.get("types", {})
        unique_patterns: list[dict] = []

        gap_keywords = ["일조", "조망", "기반시설", "주민 건강", "이주", "생활권", "홍수", "침수"]

        for kr_type, entry in types.items():
            for item in entry.get("common_issues", []):
                issue = item["issue"]
                if any(kw in issue for kw in gap_keywords):
                    unique_patterns.append({
                        "korean_type": kr_type,
                        "issue": issue,
                        "pct": item.get("pct", 0),
                        "count": item.get("count", 0),
                    })

        # 중복 제거 후 제안 생성
        seen_issues: set[str] = set()
        for pat in sorted(unique_patterns, key=lambda x: x["pct"], reverse=True):
            if pat["issue"] in seen_issues:
                continue
            seen_issues.add(pat["issue"])
            suggestions.append({
                "suggestion_id": f"SUG-{suggestion_id:03d}",
                "title": f"{pat['issue']} 검토 규칙 추가",
                "source_type": pat["korean_type"],
                "issue": pat["issue"],
                "evidence": f"과거 {pat['korean_type']} 사업에서 {pat['pct']}% 빈도로 지적",
                "recommended_severity": "review" if pat["pct"] < 40 else "major",
                "rationale": f"현재 규칙에서 '{pat['issue']}'에 대한 직접적 검토 규칙이 부재. "
                             f"과거 데이터에서 유의미한 빈도로 지적됨.",
            })
            suggestion_id += 1

        return suggestions

    def get_overall_summary(self) -> dict[str, Any]:
        """전체 분석 데이터 요약."""
        self._ensure_loaded()

        summary = self._conslt_patterns.get("summary", {})
        biz_dist = self._conslt_patterns.get("biz_type_distribution", {})
        step_dist = self._conslt_patterns.get("step_distribution", {})

        return {
            "total_count": summary.get("total_count", 0),
            "year_range": summary.get("year_range", ""),
            "analyzed_at": summary.get("analyzed_at", ""),
            "unique_biz_types": summary.get("unique_biz_types", 0),
            "biz_type_distribution": biz_dist,
            "step_distribution": step_dist,
            "available_types": list(self._patterns_by_type.get("types", {}).keys()),
        }
