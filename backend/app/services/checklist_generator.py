"""현장조사 체크리스트 생성 서비스.

리스크 카드 결과와 규제 매칭 결과를 조합하여
severity별로 그룹핑된 현장조사 체크리스트를 생성한다.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    """체크리스트 개별 항목."""

    id: int
    category: str  # severity level or "regulation"
    title: str
    description: str
    legal_basis: str | None = None
    priority: str  # "필수", "권고", "참고"
    checked: bool = False
    related_rule_id: str | None = None


class ChecklistSection(BaseModel):
    """체크리스트 섹션 (severity별 그룹)."""

    section_name: str
    priority: str
    items: list[ChecklistItem] = []


class ChecklistResponse(BaseModel):
    """현장조사 체크리스트 전체 응답."""

    screening_id: str | None = None
    total_items: int = 0
    sections: list[ChecklistSection] = []
    generated_at: str  # ISO datetime


class ChecklistGenerator:
    """리스크 카드 + 규제 매칭 결과로 현장조사 체크리스트를 생성한다."""

    SEVERITY_SECTIONS = {
        "critical": {"section_name": "즉시 확인 필요 (Critical)", "priority": "필수"},
        "major": {"section_name": "주요 검토 항목 (Major)", "priority": "필수"},
        "review": {"section_name": "추가 검토 권고 (Review)", "priority": "권고"},
        "info": {"section_name": "참고 사항 (Info)", "priority": "참고"},
    }

    SEVERITY_ORDER = ["critical", "major", "review", "info"]

    def generate(
        self,
        risk_cards: list,  # list of RiskCardResult or similar dicts
        regulation_matches: list | None = None,
        screening_id: str | None = None,
    ) -> ChecklistResponse:
        """Generate checklist from risk cards and regulation matches.

        Args:
            risk_cards: RiskCardResult 객체 또는 동일 구조의 dict 리스트.
            regulation_matches: RegulationMatchResult 객체 또는 dict 리스트 (선택).
            screening_id: 스크리닝 식별자 (선택).

        Returns:
            severity별로 그룹핑된 ChecklistResponse.
        """
        # 1. Group risk cards by severity
        severity_groups: dict[str, list] = {}
        for card in risk_cards:
            severity = self._get_attr(card, "severity", "info")
            severity_groups.setdefault(severity, []).append(card)

        # 2-3. For each severity group, create ChecklistSection with items
        sections: list[ChecklistSection] = []
        item_counter = 0

        for severity_key in self.SEVERITY_ORDER:
            cards = severity_groups.get(severity_key)
            if not cards:
                continue

            section_meta = self.SEVERITY_SECTIONS[severity_key]
            items: list[ChecklistItem] = []

            for card in cards:
                item_counter += 1
                items.append(
                    ChecklistItem(
                        id=item_counter,
                        category=severity_key,
                        title=self._get_attr(card, "title", ""),
                        description=self._get_attr(card, "next_action", ""),
                        legal_basis=self._get_attr(card, "legal_basis", None),
                        priority=section_meta["priority"],
                        checked=False,
                        related_rule_id=self._get_attr(card, "rule_id", None),
                    )
                )

            sections.append(
                ChecklistSection(
                    section_name=section_meta["section_name"],
                    priority=section_meta["priority"],
                    items=items,
                )
            )

        # 4. If regulation_matches provided, add a "규제 확인 사항" section
        if regulation_matches:
            reg_items: list[ChecklistItem] = []
            for reg in regulation_matches:
                permit_required = self._get_attr(reg, "permit_required", False)
                if not permit_required:
                    continue

                item_counter += 1
                regulation_name = self._get_attr(reg, "regulation_name", "")
                description = self._get_attr(reg, "description", "")
                related_authority = self._get_attr(reg, "related_authority", "")
                if related_authority:
                    description = f"{description} (관할: {related_authority})"

                reg_items.append(
                    ChecklistItem(
                        id=item_counter,
                        category="regulation",
                        title=regulation_name,
                        description=description,
                        legal_basis=self._get_attr(reg, "legal_basis", None),
                        priority="필수",
                        checked=False,
                        related_rule_id=self._get_attr(
                            reg, "regulation_code", None
                        ),
                    )
                )

            if reg_items:
                sections.append(
                    ChecklistSection(
                        section_name="규제 확인 사항",
                        priority="필수",
                        items=reg_items,
                    )
                )

        # 5-6. Build and return response
        total_items = sum(len(section.items) for section in sections)
        return ChecklistResponse(
            screening_id=screening_id,
            total_items=total_items,
            sections=sections,
            generated_at=datetime.now().isoformat(),
        )

    def to_pdf_structure(self, checklist: ChecklistResponse) -> dict:
        """PDF 출력용 구조를 생성한다.

        Args:
            checklist: generate()로 생성된 ChecklistResponse.

        Returns:
            PDF 렌더링에 적합한 dict 구조.
        """
        pdf_sections = []
        for section in checklist.sections:
            pdf_items = []
            for item in section.items:
                pdf_items.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "description": item.description,
                        "legal_basis": item.legal_basis,
                        "priority": item.priority,
                        "checked": item.checked,
                    }
                )
            pdf_sections.append(
                {
                    "section_name": section.section_name,
                    "items": pdf_items,
                }
            )

        return {
            "title": "현장조사 체크리스트",
            "screening_id": checklist.screening_id,
            "generated_at": checklist.generated_at,
            "sections": pdf_sections,
        }

    @staticmethod
    def _get_attr(obj: object, key: str, default=None):
        """객체 또는 dict에서 속성/키를 안전하게 추출한다."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
