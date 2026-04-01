"""검토의견 예측 서비스.

과거 환경영향평가 협의 데이터에서 검토관이 자주 지적하는 패턴을 기반으로
예상 검토의견을 생성한다. 각 의견에 확률(%)과 과거 근거 사례 수를 표시한다.
"""

import logging
from typing import Any

from backend.app.services.pattern_advisor import PatternAdvisor

logger = logging.getLogger(__name__)

# 이슈 키워드 → 검토의견 매핑 레지스트리
# 패턴 데이터의 common_issues 텍스트를 검토의견 카테고리 + 코멘트로 변환한다.
# 유형별 코멘트 변형(variants)이 있으면 해당 유형의 코멘트를 사용한다.
_ISSUE_COMMENT_REGISTRY: list[dict[str, Any]] = [
    {
        "match_keywords": ["소음", "진동"],
        "category": "소음·진동",
        "default_comment": "공사 중 및 운영 시 소음·진동 저감대책이 불충분합니다. 방음벽 설치 위치·높이 등 구체적 대안을 제시하시기 바랍니다.",
        "type_comments": {
            "공항": "항공기 운항에 의한 소음 영향을 정밀 예측하고, 소음대책지역 설정 및 방음시설 설치 계획을 구체적으로 제시하시기 바랍니다.",
            "철도": "열차 운행에 따른 소음·진동 영향 예측 및 주거지역 인접 구간 방음벽·방진 궤도 설치 계획을 구체적으로 제시하시기 바랍니다.",
            "발전소": "발전시설 운전 소음의 영향 범위 및 방음대책을 구체화하시기 바랍니다.",
            "산업단지": "산업단지 경계 소음 예측 및 주거지역 이격거리 확보 방안을 검토하시기 바랍니다.",
            "주거단지": "인접 기존 주거지역에 대한 소음·진동 영향을 예측하고, 배치 변경 등 근본적 저감대책을 검토하시기 바랍니다.",
        },
        "trigger_keywords": ["소음", "진동"],
    },
    {
        "match_keywords": ["생태", "서식지", "녹지"],
        "category": "생태계",
        "default_comment": "사업지 인근 생태계에 대한 4계절 정밀 조사가 필요하며, 생태통로 설치 등 서식지 단절 방지 대책을 보완하시기 바랍니다.",
        "type_comments": {
            "철도": "노선 통과 지역의 생태계 단절 영향을 분석하고, 생태통로 설치 및 야생동물 이동로 보전 대책을 구체적으로 제시하시기 바랍니다.",
            "공항": "사업지 일대 생태계 정밀 조사를 실시하고, 서식지 훼손에 대한 대체서식지 조성 계획을 제시하시기 바랍니다.",
            "관광단지": "사업지 및 주변 생태계에 대한 4계절 정밀 조사를 실시하고, 핵심 생태축 보전 대책을 구체적으로 제시하시기 바랍니다.",
            "주거단지": "생태면적률 확보 방안 및 대체서식지 조성 계획을 보완하시기 바랍니다.",
        },
        "trigger_keywords": ["생태", "서식지", "멸종", "단절"],
    },
    {
        "match_keywords": ["대기", "분진", "배출"],
        "category": "대기질",
        "default_comment": "공사 시 비산먼지 저감대책과 운영 시 배기가스 영향을 구체적으로 예측하시기 바랍니다.",
        "type_comments": {
            "발전소": "AERMOD 등 대기확산 모델링을 통한 정량적 영향 예측 및 배출가스 저감시설(SCR 등) 효율을 구체적으로 제시하시기 바랍니다.",
            "산업단지": "입주 업종별 대기오염물질 배출량을 산정하고, 완충녹지대(50m 이상) 조성 계획을 구체화하시기 바랍니다.",
            "공항": "항공기 엔진 배출가스 및 지상 조업 장비에 의한 대기질 영향을 정량적으로 예측하시기 바랍니다.",
            "주거단지": "공사 중 분진 및 운영 시 차량 배기가스에 의한 대기질 영향을 정량적으로 예측하고 저감대책을 보완하시기 바랍니다.",
        },
        "trigger_keywords": ["대기", "분진", "PM", "배출"],
    },
    {
        "match_keywords": ["수질", "오염", "하수", "온배수", "비점오염"],
        "category": "수질",
        "default_comment": "비점오염원 저감시설 설치 계획 및 수질 모니터링 방안을 보완하시기 바랍니다.",
        "type_comments": {
            "발전소": "온배수 확산 예측 및 냉각수 순환 시스템, 해양 수질 영향을 정밀 분석하시기 바랍니다.",
            "산업단지": "폐수종말처리시설 용량 및 방류수 수질 기준 적합성을 검증하시기 바랍니다.",
            "주거단지": "생활하수 발생량 및 하수처리시설 용량 적정성을 검토하고, 중수도 설치 방안을 제시하시기 바랍니다.",
            "철도": "터널 용출수 및 공사 중 비점오염원 처리 대책을 구체적으로 제시하시기 바랍니다.",
            "관광단지": "관광시설 운영 시 발생하는 오수·우수의 처리 및 비점오염원 저감 대책을 보완하시기 바랍니다.",
            "하천": "하천 수질 영향 예측 및 수질 모니터링 방안을 구체적으로 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["수질", "오염", "수변", "온배수", "하수"],
    },
    {
        "match_keywords": ["농지", "산지", "전용"],
        "category": "농지·산지",
        "default_comment": "농지전용 및 산지전용에 따른 대체 조성 계획을 구체적으로 제시하시기 바랍니다.",
        "trigger_keywords": ["농지", "산지", "농업진흥", "전용"],
    },
    {
        "match_keywords": ["경관"],
        "category": "경관",
        "default_comment": "주요 조망점에서의 경관 변화를 시뮬레이션하고, 경관 영향 저감대책을 구체적으로 제시하시기 바랍니다.",
        "type_comments": {
            "관광단지": "관광단지 조성에 따른 자연경관 훼손을 최소화하고, 주요 조망점에서의 경관 영향 저감대책을 제시하시기 바랍니다.",
            "공항": "활주로·터미널 등 시설물에 의한 경관 변화를 분석하고, 시각적 영향 저감대책을 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["경관", "조망", "스카이라인"],
    },
    {
        "match_keywords": ["교통"],
        "category": "교통",
        "default_comment": "사업 시행에 따른 교통량 증가 영향을 예측하고, 대중교통 연계 및 교통 개선 방안을 구체적으로 제시하시기 바랍니다.",
        "type_comments": {
            "주거단지": "입주 후 교통량 증가에 대한 영향을 예측하고, 대중교통 연계 방안을 구체화하시기 바랍니다.",
            "산업단지": "물류 차량 동선 분리 및 진입도로 확장 계획을 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["교통", "차량", "물류"],
    },
    {
        "match_keywords": ["지형", "지질", "터널", "절토"],
        "category": "지형·지질",
        "default_comment": "절토·성토에 따른 지형 변화와 사면 안정성 분석 결과를 제시하시기 바랍니다.",
        "type_comments": {
            "철도": "터널 굴착 및 절성토에 따른 지형·지질 변화 영향과 사면 안정성 확보 대책을 구체적으로 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["지형", "지질", "절토", "터널"],
    },
    {
        "match_keywords": ["온실가스", "탄소"],
        "category": "온실가스",
        "default_comment": "온실가스 배출량 산정 및 감축 계획, 탄소상쇄 방안을 제시하시기 바랍니다.",
        "trigger_keywords": ["온실가스", "탄소"],
    },
    {
        "match_keywords": ["해양", "수생태"],
        "category": "해양생태",
        "default_comment": "해양생태계에 대한 정밀 조사를 실시하고, 해양환경 영향 저감대책을 구체적으로 제시하시기 바랍니다.",
        "type_comments": {
            "항만": "해양 생태계 영향 조사 및 항만 준설·매립에 따른 해양환경 변화 예측과 저감대책을 구체화하시기 바랍니다.",
            "발전소": "온배수에 의한 해양생태계 영향 및 인공어초 등 보상 방안을 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["해양", "수생태"],
    },
    {
        "match_keywords": ["조류충돌", "조류", "Bird Strike"],
        "category": "조류충돌",
        "default_comment": "조류 이동 경로 및 서식 현황을 조사하고, 조류충돌 방지 대책을 구체적으로 제시하시기 바랍니다.",
        "type_comments": {
            "공항": "항공기 조류충돌(Bird Strike) 위험도를 분석하고, 조류 퇴치 계획 및 공항 주변 조류 유인시설 관리 방안을 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["조류", "Bird Strike"],
    },
    {
        "match_keywords": ["문화재"],
        "category": "문화재",
        "default_comment": "사업지 내 매장문화재 유존 가능성을 조사하고, 문화재 영향 저감대책을 수립하시기 바랍니다.",
        "trigger_keywords": ["문화재"],
    },
    {
        "match_keywords": ["토양"],
        "category": "토양",
        "default_comment": "토양오염 방지시설 및 지하수 모니터링정 설치 계획을 보완하시기 바랍니다.",
        "trigger_keywords": ["토양", "지하수"],
    },
    {
        "match_keywords": ["폐기물", "준설토"],
        "category": "폐기물",
        "default_comment": "공사 및 운영 시 발생 폐기물 처리 계획을 구체적으로 제시하시기 바랍니다.",
        "trigger_keywords": ["폐기물", "준설토"],
    },
    {
        "match_keywords": ["주민", "이주", "생활권"],
        "category": "주민생활",
        "default_comment": "사업 시행에 따른 주민 생활환경 영향을 분석하고, 주민 의견 수렴 및 피해 최소화 방안을 제시하시기 바랍니다.",
        "trigger_keywords": ["주민", "이주", "생활권"],
    },
    {
        "match_keywords": ["지하수", "함양"],
        "category": "지하수",
        "default_comment": "지하수 함양률 저감 및 지하수위 변화에 대한 영향을 분석하고, 침투시설 설치 등 저감대책을 제시하시기 바랍니다.",
        "type_comments": {
            "공항": "활주로·계류장 포장에 따른 지하수 함양률 저감 영향과 대체 침투시설 설치 계획을 제시하시기 바랍니다.",
            "철도": "터널 굴착에 따른 지하수 유출·고갈 영향을 분석하고, 차수·보강 대책을 구체적으로 제시하시기 바랍니다.",
        },
        "trigger_keywords": ["지하수", "함양"],
    },
    {
        "match_keywords": ["어업", "수산", "어류"],
        "category": "어업",
        "default_comment": "어업권 및 수산자원에 대한 영향을 조사하고, 어업 피해 보상 방안을 구체적으로 제시하시기 바랍니다.",
        "trigger_keywords": ["어업", "수산", "어류"],
    },
    {
        "match_keywords": ["일조", "조망권"],
        "category": "일조·조망",
        "default_comment": "일조권 및 조망권 영향을 분석하고, 건축물 높이·배치 조정 등 저감대책을 제시하시기 바랍니다.",
        "trigger_keywords": ["일조", "조망"],
    },
    {
        "match_keywords": ["기반시설", "인프라"],
        "category": "기반시설",
        "default_comment": "상하수도, 전력 등 기반시설 수용 용량 적정성을 검토하시기 바랍니다.",
        "trigger_keywords": ["기반시설", "인프라"],
    },
    {
        "match_keywords": ["하천", "어류 서식"],
        "category": "하천생태",
        "default_comment": "하천 생태계 영향 및 어류 서식지 보전 대책을 구체적으로 제시하시기 바랍니다.",
        "trigger_keywords": ["하천", "어류"],
    },
]


def _match_issue_to_comment(issue_name: str, kr_type: str) -> dict[str, Any] | None:
    """패턴 데이터의 이슈명을 검토의견 레지스트리에서 매칭한다."""
    for entry in _ISSUE_COMMENT_REGISTRY:
        if any(kw in issue_name for kw in entry["match_keywords"]):
            type_comments = entry.get("type_comments", {})
            comment = type_comments.get(kr_type, entry["default_comment"])
            return {
                "category": entry["category"],
                "comment": comment,
                "trigger_keywords": entry["trigger_keywords"],
            }
    return None


class ReviewPredictor:
    """검토의견 예측 서비스."""

    def __init__(self) -> None:
        self._advisor = PatternAdvisor()
        self._advisor.load()

    def predict_review_comments(
        self,
        project_type: str,
        risk_cards: list[dict[str, Any]] | None = None,
        draft_sections: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """예상 검토의견을 생성한다.

        패턴 데이터의 common_issues를 기반으로 유형별 확률을 반영한
        검토의견을 생성한다. 패턴 데이터가 없으면 기본 템플릿을 사용한다.

        Args:
            project_type: 사업유형 (road, airport, railway, tourism, ...)
            risk_cards: 리스크 카드 목록 (선택 — 확률 보정에 사용)
            draft_sections: 초안 섹션 목록 (선택 — 누락 체크에 사용)

        Returns:
            {
                "project_type": str,
                "korean_type": str,
                "total_past_cases": int,
                "predicted_comments": [...],
                "avg_review_months": float | None,
                "supplement_required_pct": float | None,
                "disclaimer": str,
            }
        """
        risk_cards = risk_cards or []

        # 패턴 데이터 가져오기
        patterns = self._advisor.predict_issues(project_type)
        kr_type = patterns.get("korean_type", "기타")
        total = patterns.get("total_in_type", 0)
        common_issues = patterns.get("predicted_issues", [])

        # 패턴 데이터 기반 생성 (common_issues가 있는 경우)
        if common_issues and total > 0:
            predicted_comments = self._from_pattern_data(
                kr_type, total, common_issues, risk_cards,
            )
        else:
            # 패턴 데이터 없음 → 기본 검토의견 (확률 없이)
            predicted_comments = self._default_comments(risk_cards)

        # 확률순 정렬, 상위 5개
        predicted_comments.sort(key=lambda x: -x["probability_pct"])
        predicted_comments = predicted_comments[:5]

        return {
            "project_type": project_type,
            "korean_type": kr_type,
            "total_past_cases": total,
            "predicted_comments": predicted_comments,
            "avg_review_months": patterns.get("avg_review_months"),
            "supplement_required_pct": patterns.get("supplement_required_pct"),
            "disclaimer": "이 예측은 과거 통계 기반 참고 자료이며, 실제 검토의견과 다를 수 있습니다",
        }

    def _from_pattern_data(
        self,
        kr_type: str,
        total: int,
        common_issues: list[dict[str, Any]],
        risk_cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """패턴 데이터의 common_issues를 검토의견으로 변환."""
        results: list[dict[str, Any]] = []
        seen_categories: set[str] = set()

        for issue_data in common_issues[:10]:
            issue_name = issue_data["issue"]
            probability = issue_data["probability_pct"]
            past_count = issue_data["past_count"]

            matched = _match_issue_to_comment(issue_name, kr_type)
            if not matched:
                continue

            # 같은 카테고리 중복 방지
            if matched["category"] in seen_categories:
                continue
            seen_categories.add(matched["category"])

            # 리스크 카드 매칭 시 확률 소폭 상향 (+5%)
            has_matching_risk = any(
                any(kw in str(card.get("title", "")) + str(card.get("rationale", ""))
                    for kw in matched["trigger_keywords"])
                for card in risk_cards
            )
            if has_matching_risk:
                probability = min(probability + 5.0, 99.0)

            results.append({
                "category": matched["category"],
                "comment": matched["comment"],
                "probability_pct": round(probability, 1),
                "past_count": past_count,
                "total_past_cases": issue_data.get("total_in_type", total),
                "risk_matched": has_matching_risk,
                "severity": self._estimate_severity(probability),
            })

        return results

    def _default_comments(
        self, risk_cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """패턴 데이터가 없을 때 기본 검토의견."""
        defaults = [
            ("소음·진동", "소음·진동 저감대책의 구체성을 보완하시기 바랍니다.", ["소음", "진동"], 50.0),
            ("생태계", "생태계 영향 조사 및 보전 대책을 보완하시기 바랍니다.", ["생태", "서식지"], 45.0),
            ("수질", "수질 영향 예측 및 저감 대책을 보완하시기 바랍니다.", ["수질", "오염"], 40.0),
            ("대기질", "대기질 영향 예측 및 저감 대책을 보완하시기 바랍니다.", ["대기", "분진"], 38.0),
            ("농지·산지", "토지 전용에 따른 대체 조성 계획을 제시하시기 바랍니다.", ["농지", "산지"], 35.0),
            ("악취", "악취 영향 예측 및 방지시설 설치 계획을 보완하시기 바랍니다.", ["악취", "악취관리"], 30.0),
        ]
        results = []
        for cat, comment, keywords, prob in defaults:
            has_risk = any(
                any(kw in str(card.get("title", "")) + str(card.get("rationale", ""))
                    for kw in keywords)
                for card in risk_cards
            )
            if has_risk:
                prob = min(prob + 5.0, 99.0)
            results.append({
                "category": cat,
                "comment": comment,
                "probability_pct": round(prob, 1),
                "past_count": 0,
                "total_past_cases": 0,
                "risk_matched": has_risk,
                "severity": self._estimate_severity(prob),
            })
        return results

    @staticmethod
    def _estimate_severity(probability: float) -> str:
        """확률에 따른 심각도 추정."""
        if probability >= 70:
            return "high"
        if probability >= 40:
            return "medium"
        return "low"
