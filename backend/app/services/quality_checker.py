"""평가서 품질 자동 체크 서비스.

생성된 초안 또는 스크리닝 데이터를 대상으로:
- 필수 평가항목 누락 확인
- 데이터 일관성 확인
- 법적 요구사항 충족 여부 확인
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 필수 평가항목 (환경영향평가서 작성 안내서 기준)
_REQUIRED_SECTIONS = [
    {"section_id": "ch1_s1", "title": "사업의 목적 및 필요성", "category": "사업 개요"},
    {"section_id": "ch1_s2", "title": "사업의 내용", "category": "사업 개요"},
    {"section_id": "ch1_s3", "title": "관련 법규 및 계획", "category": "사업 개요"},
    {"section_id": "ch2_s1", "title": "자연환경 현황", "category": "지역 개황"},
    {"section_id": "ch2_s2", "title": "생활환경 현황", "category": "지역 개황"},
    {"section_id": "ch3_s1", "title": "대기질", "category": "평가 항목"},
    {"section_id": "ch3_s2", "title": "수질", "category": "평가 항목"},
    {"section_id": "ch3_s3", "title": "소음·진동", "category": "평가 항목"},
    {"section_id": "ch3_s5", "title": "생태계", "category": "평가 항목"},
    {"section_id": "ch4_s1", "title": "공사 시 저감 방안", "category": "저감 방안"},
    {"section_id": "ch4_s2", "title": "운영 시 저감 방안", "category": "저감 방안"},
    {"section_id": "ch5_s1", "title": "환경영향 종합 평가", "category": "종합 평가"},
    {"section_id": "ch6_s1", "title": "사후환경영향조사 계획", "category": "사후 조사"},
]

# 사업유형별 필수 법적 검토 사항
_LEGAL_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "road": [
        {"requirement": "환경영향평가법 제22조에 따른 평가서 작성", "check": "평가서 구성"},
        {"requirement": "소음·진동관리법에 따른 소음 예측", "check": "소음 섹션"},
        {"requirement": "자연환경보전법에 따른 생태조사", "check": "생태 섹션"},
        {"requirement": "대기환경보전법에 따른 대기영향 분석", "check": "대기 섹션"},
    ],
    "housing": [
        {"requirement": "환경영향평가법 제22조에 따른 평가서 작성", "check": "평가서 구성"},
        {"requirement": "대기환경보전법에 따른 대기영향 분석", "check": "대기 섹션"},
        {"requirement": "물환경보전법에 따른 수질영향 분석", "check": "수질 섹션"},
        {"requirement": "소음·진동관리법에 따른 소음 예측", "check": "소음 섹션"},
    ],
    "power_plant": [
        {"requirement": "환경영향평가법 제22조에 따른 평가서 작성", "check": "평가서 구성"},
        {"requirement": "대기환경보전법에 따른 대기확산 모델링", "check": "대기 섹션"},
        {"requirement": "온실가스 배출권거래법에 따른 배출량 산정", "check": "온실가스"},
        {"requirement": "해양환경관리법에 따른 해양영향 분석", "check": "해양 섹션"},
    ],
    "factory": [
        {"requirement": "환경영향평가법 제22조에 따른 평가서 작성", "check": "평가서 구성"},
        {"requirement": "대기환경보전법에 따른 배출영향 분석", "check": "대기 섹션"},
        {"requirement": "물환경보전법에 따른 폐수처리 검토", "check": "수질 섹션"},
        {"requirement": "토양환경보전법에 따른 토양오염 방지", "check": "토양 섹션"},
    ],
}

# 데이터 일관성 검사 규칙
_CONSISTENCY_RULES = [
    {
        "rule_id": "CON-001",
        "description": "리스크 카드가 있으면 해당 항목의 저감 방안이 존재해야 함",
        "category": "저감 방안 매칭",
    },
    {
        "rule_id": "CON-002",
        "description": "Critical/Major 리스크가 있으면 관련 법적 근거가 명시되어야 함",
        "category": "법적 근거 완전성",
    },
    {
        "rule_id": "CON-003",
        "description": "현장조사 필요 섹션에 실측 데이터 포함 여부",
        "category": "현장조사 데이터",
    },
    {
        "rule_id": "CON-004",
        "description": "사후환경영향조사 항목이 평가 항목과 일치해야 함",
        "category": "사후 조사 일관성",
    },
]


class QualityChecker:
    """평가서 품질 자동 체크 서비스."""

    def check(
        self,
        project_type: str,
        risk_cards: list[dict[str, Any]] | None = None,
        regulations: list[dict[str, Any]] | None = None,
        draft_sections: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """품질 체크를 수행한다.

        Returns:
            {
                "overall_status": "pass" | "warning" | "fail",
                "score": int (0~100),
                "checks": [...],
                "summary": {...},
            }
        """
        risk_cards = risk_cards or []
        regulations = regulations or []
        draft_sections = draft_sections or []

        checks: list[dict[str, Any]] = []

        # 1. 필수 섹션 누락 확인
        checks.extend(self._check_required_sections(draft_sections))

        # 2. 법적 요구사항 충족
        checks.extend(self._check_legal_requirements(project_type, draft_sections))

        # 3. 리스크-저감 방안 매칭
        checks.extend(self._check_risk_mitigation_match(risk_cards, draft_sections))

        # 4. 법적 근거 완전성
        checks.extend(self._check_legal_basis_completeness(risk_cards))

        # 5. 현장조사 필요 항목 확인
        checks.extend(self._check_field_survey_items(draft_sections))

        # 6. 면책 문구 포함 확인
        checks.extend(self._check_disclaimer(draft_sections))

        # 점수 계산
        total = len(checks)
        passed = sum(1 for c in checks if c["status"] == "pass")
        warnings = sum(1 for c in checks if c["status"] == "warning")
        failed = sum(1 for c in checks if c["status"] == "fail")
        score = int((passed / total * 100)) if total > 0 else 0

        if failed > 0:
            overall = "fail"
        elif warnings > 0:
            overall = "warning"
        else:
            overall = "pass"

        return {
            "overall_status": overall,
            "score": score,
            "total_checks": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "checks": checks,
            "summary": {
                "필수 섹션": f"{self._count_by_category(checks, '필수 섹션')}",
                "법적 요구사항": f"{self._count_by_category(checks, '법적 요구사항')}",
                "리스크 대응": f"{self._count_by_category(checks, '리스크 대응')}",
                "데이터 품질": f"{self._count_by_category(checks, '데이터 품질')}",
            },
        }

    def _check_required_sections(
        self, draft_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """필수 평가항목 누락 확인."""
        existing_ids = {s.get("section_id") for s in draft_sections}
        checks = []

        for req in _REQUIRED_SECTIONS:
            if existing_ids and req["section_id"] in existing_ids:
                # 내용이 비어있는지도 확인
                section = next(
                    (s for s in draft_sections if s.get("section_id") == req["section_id"]),
                    None,
                )
                content = section.get("content", "") if section else ""
                if len(content) < 50:
                    checks.append({
                        "check_id": f"REQ-{req['section_id']}",
                        "category": "필수 섹션",
                        "title": f"{req['title']} 내용 부족",
                        "status": "warning",
                        "detail": f"'{req['title']}' 섹션의 내용이 부족합니다 (현재 {len(content)}자).",
                    })
                else:
                    checks.append({
                        "check_id": f"REQ-{req['section_id']}",
                        "category": "필수 섹션",
                        "title": f"{req['title']}",
                        "status": "pass",
                        "detail": f"'{req['title']}' 섹션이 포함되었습니다.",
                    })
            else:
                status = "fail" if not draft_sections else "warning"
                checks.append({
                    "check_id": f"REQ-{req['section_id']}",
                    "category": "필수 섹션",
                    "title": f"{req['title']} 누락",
                    "status": status,
                    "detail": f"필수 섹션 '{req['title']}'이(가) 누락되었습니다.",
                })

        return checks

    def _check_legal_requirements(
        self, project_type: str, draft_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """법적 요구사항 충족 확인."""
        requirements = _LEGAL_REQUIREMENTS.get(project_type, _LEGAL_REQUIREMENTS.get("road", []))
        checks = []

        for req in requirements:
            # 간단한 키워드 매칭으로 충족 여부 확인
            all_content = " ".join(s.get("content", "") for s in draft_sections)
            keywords = req["check"].replace(" 섹션", "").split()

            found = any(kw in all_content for kw in keywords)
            checks.append({
                "check_id": f"LAW-{requirements.index(req) + 1:02d}",
                "category": "법적 요구사항",
                "title": req["requirement"],
                "status": "pass" if found or not draft_sections else "warning",
                "detail": req["requirement"],
            })

        return checks

    def _check_risk_mitigation_match(
        self,
        risk_cards: list[dict[str, Any]],
        draft_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """리스크 카드에 대응하는 저감 방안 존재 여부."""
        checks = []
        mitigation_content = " ".join(
            s.get("content", "")
            for s in draft_sections
            if s.get("section_id", "").startswith("ch4")
        )

        major_risks = [c for c in risk_cards if c.get("severity") in ("critical", "major")]

        for card in major_risks[:5]:
            title = card.get("title", "")
            # 리스크 제목 키워드가 저감 방안에 포함되는지 확인
            keywords = title.replace("—", " ").replace("·", " ").split()[:3]
            found = any(kw in mitigation_content for kw in keywords if len(kw) >= 2)

            checks.append({
                "check_id": f"MIT-{card.get('rule_id', 'N/A')}",
                "category": "리스크 대응",
                "title": f"{title} 저감 방안",
                "status": "pass" if found or not draft_sections else "warning",
                "detail": f"리스크 '{title}'에 대한 저감 방안 {'확인됨' if found else '미확인'}",
            })

        return checks

    def _check_legal_basis_completeness(
        self, risk_cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Critical/Major 리스크의 법적 근거 명시 여부."""
        checks = []
        major_risks = [c for c in risk_cards if c.get("severity") in ("critical", "major")]

        for card in major_risks[:5]:
            has_basis = bool(card.get("legal_basis"))
            checks.append({
                "check_id": f"LB-{card.get('rule_id', 'N/A')}",
                "category": "데이터 품질",
                "title": f"{card.get('title', '')} 법적 근거",
                "status": "pass" if has_basis else "warning",
                "detail": f"법적 근거: {card.get('legal_basis', '미기재')}",
            })

        return checks

    def _check_field_survey_items(
        self, draft_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """현장조사 필요 항목에 실측 데이터 여부 확인."""
        checks = []

        for section in draft_sections:
            if section.get("field_survey_required"):
                content = section.get("content", "")
                has_measured = any(
                    kw in content
                    for kw in ["실측", "측정 결과", "조사 결과", "현장 조사"]
                )
                checks.append({
                    "check_id": f"FS-{section.get('section_id', 'N/A')}",
                    "category": "데이터 품질",
                    "title": f"{section.get('title', '')} 현장 데이터",
                    "status": "pass" if has_measured else "warning",
                    "detail": (
                        f"'{section.get('title', '')}'에 현장 실측 데이터가 "
                        f"{'포함' if has_measured else '미포함'}되었습니다."
                    ),
                })

        return checks

    def _check_disclaimer(
        self, draft_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """AI 면책 문구 포함 확인."""
        if not draft_sections:
            return [{
                "check_id": "DISC-001",
                "category": "데이터 품질",
                "title": "AI 면책 문구",
                "status": "warning",
                "detail": "초안이 없어 면책 문구 확인 불가",
            }]

        all_content = " ".join(s.get("content", "") for s in draft_sections)
        has_disclaimer = "참고 자료" in all_content or "전문가 검토" in all_content

        return [{
            "check_id": "DISC-001",
            "category": "데이터 품질",
            "title": "AI 면책 문구",
            "status": "pass" if has_disclaimer else "fail",
            "detail": "AI 생성 면책 문구가 " + ("포함" if has_disclaimer else "누락") + "되었습니다.",
        }]

    @staticmethod
    def _count_by_category(checks: list[dict[str, Any]], category: str) -> str:
        """카테고리별 통과/전체 비율."""
        cat_checks = [c for c in checks if c["category"] == category]
        if not cat_checks:
            return "N/A"
        passed = sum(1 for c in cat_checks if c["status"] == "pass")
        return f"{passed}/{len(cat_checks)} 통과"
