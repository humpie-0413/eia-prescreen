"""평가서 초안 자동 생성 서비스 (Draft Copilot).

환경영향평가서 표준 목차에 따라 섹션별 초안을 생성한다.
- 사업 개요: 입력 데이터에서 자동
- 지역 개황: 커넥터 데이터에서 자동
- 평가 항목별 현황: API 데이터 + 과거 패턴에서 자동
- 환경영향 예측: 과거 패턴 기반 초안 + "전문가 검토 필요" 표시
- 저감 방안: 과거 유사사례의 저감방안 참조

모든 초안에 "이 초안은 AI가 생성한 참고 자료이며 전문가 검토가 필요합니다" 명시.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from backend.app.core.config import settings
from backend.app.services.pattern_advisor import PatternAdvisor
from backend.app.services.report_rag import ReportRAG

logger = logging.getLogger(__name__)

_DISCLAIMER = "이 초안은 AI가 생성한 참고 자료이며 전문가 검토가 필요합니다"

_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "templates" / "eia_report_template.json"
)

# 사업유형 한국어 매핑 (환경영향평가법 시행령 별표3 기준 17개 유형)
# 사업유형별 중점 평가 섹션 (해당 섹션에 "중점" 배지 부여)
_TYPE_EMPHASIS: dict[str, list[str]] = {
    "energy": ["ch3_s1", "ch3_s8"],       # 대기+온실가스
    "port": ["ch3_s7", "ch3_s2"],          # 해양+수질
    "reclamation": ["ch3_s7", "ch3_s5"],   # 해양+생태
    "industrial": ["ch3_s1", "ch3_s9"],    # 대기+악취
    "waste": ["ch3_s1", "ch3_s9"],         # 대기+악취
    "tourism": ["ch3_s6", "ch3_s5"],       # 경관+생태
    "road": ["ch3_s3", "ch3_s5"],          # 소음+생태
    "railway": ["ch3_s3", "ch3_s5"],       # 소음+생태
    "river": ["ch3_s2", "ch3_s7"],         # 수질+해양
    "urban_dev": ["ch3_s1", "ch3_s3"],     # 대기+소음
    "water_resource": ["ch3_s2", "ch3_s5"],# 수질+생태
    "mountain": ["ch3_s5", "ch3_s4"],      # 생태+토양
    "mining": ["ch3_s4", "ch3_s1"],        # 토양+대기
}

_TYPE_LABELS: dict[str, str] = {
    "urban_dev": "도시개발", "industrial": "산업입지",
    "energy": "에너지개발", "port": "항만건설",
    "road": "도로건설", "water_resource": "수자원개발",
    "railway": "철도건설", "airport": "공항건설",
    "river": "하천이용개발", "tourism": "관광단지개발",
    "mountain": "산지개발", "sports": "체육시설",
    "waste": "폐기물처리시설", "military": "국방군사시설",
    "mining": "토석광물채취", "reclamation": "매립간척",
    "etc": "기타",
    # 이전 호환
    "power_plant": "에너지개발", "factory": "산업입지",
    "housing": "도시개발", "other": "기타",
}


def _load_template() -> dict:
    """평가서 템플릿 JSON을 로드한다."""
    if not _TEMPLATE_PATH.exists():
        logger.warning("평가서 템플릿 없음: %s", _TEMPLATE_PATH)
        return {}
    return json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))


class DraftCopilot:
    """환경영향평가서 초안 생성 서비스."""

    def __init__(self) -> None:
        self._template = _load_template()
        self._advisor = PatternAdvisor()
        self._advisor.load()
        self._rag = ReportRAG()
        try:
            self._rag.load()
        except Exception:
            logger.warning("RAG 서비스 로드 실패 — RAG 참조 없이 동작합니다.")

    async def generate_full_draft(
        self,
        project_info: dict[str, Any],
        risk_cards: list[dict[str, Any]] | None = None,
        regulations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """전체 초안을 생성한다.

        Args:
            project_info: 사업 정보 (project_name, project_type, project_scale, address)
            risk_cards: 리스크 카드 목록 (선택)
            regulations: 규제 매칭 결과 (선택)

        Returns:
            {"sections": [...], "generated_at": str, "disclaimer": str}
        """
        risk_cards = risk_cards or []
        regulations = regulations or []

        project_type = project_info.get("project_type", "other")
        patterns = self._advisor.predict_issues(project_type)
        emphasis_sections = _TYPE_EMPHASIS.get(project_type, [])

        sections = []
        chapters = self._template.get("chapters", [])

        for chapter in chapters:
            for section in chapter.get("sections", []):
                section_id = section["section_id"]
                content = self._generate_section_content(
                    section_id=section_id,
                    section_meta=section,
                    chapter_title=chapter["title"],
                    project_info=project_info,
                    risk_cards=risk_cards,
                    regulations=regulations,
                    patterns=patterns,
                )
                badge = self._get_badge(section)
                if section_id in emphasis_sections:
                    badge = "중점 평가"
                sections.append({
                    "section_id": section_id,
                    "chapter": chapter["title"],
                    "title": section["title"],
                    "content": content,
                    "auto_generated": section.get("auto_generable", False),
                    "field_survey_required": section.get("field_survey_required", False),
                    "badge": badge,
                })

        return {
            "project_info": project_info,
            "sections": sections,
            "total_sections": len(sections),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
        }

    async def generate_section(
        self,
        section_id: str,
        project_info: dict[str, Any],
        risk_cards: list[dict[str, Any]] | None = None,
        regulations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """특정 섹션의 초안만 생성한다."""
        risk_cards = risk_cards or []
        regulations = regulations or []

        project_type = project_info.get("project_type", "other")
        patterns = self._advisor.predict_issues(project_type)

        for chapter in self._template.get("chapters", []):
            for section in chapter.get("sections", []):
                if section["section_id"] == section_id:
                    content = self._generate_section_content(
                        section_id=section_id,
                        section_meta=section,
                        chapter_title=chapter["title"],
                        project_info=project_info,
                        risk_cards=risk_cards,
                        regulations=regulations,
                        patterns=patterns,
                    )
                    return {
                        "section_id": section_id,
                        "chapter": chapter["title"],
                        "title": section["title"],
                        "content": content,
                        "auto_generated": section.get("auto_generable", False),
                        "field_survey_required": section.get("field_survey_required", False),
                        "badge": self._get_badge(section),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "disclaimer": _DISCLAIMER,
                    }
        return None

    async def generate_with_llm(
        self,
        section_id: str,
        project_info: dict[str, Any],
        risk_cards: list[dict[str, Any]] | None = None,
        regulations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """LLM을 사용하여 특정 섹션의 초안을 생성한다."""
        risk_cards = risk_cards or []
        regulations = regulations or []

        if not settings.OPENROUTER_API_KEY:
            return await self.generate_section(
                section_id, project_info, risk_cards, regulations,
            )

        project_type = project_info.get("project_type", "other")
        patterns = self._advisor.predict_issues(project_type)

        for chapter in self._template.get("chapters", []):
            for section in chapter.get("sections", []):
                if section["section_id"] == section_id:
                    # RAG 참조 가져오기
                    rag_reference = await self._get_rag_reference(
                        section["title"], project_type, risk_cards,
                    )

                    prompt = self._build_llm_prompt(
                        section_meta=section,
                        chapter_title=chapter["title"],
                        project_info=project_info,
                        risk_cards=risk_cards,
                        regulations=regulations,
                        patterns=patterns,
                        rag_reference=rag_reference,
                    )
                    content = await self._call_llm(prompt)

                    return {
                        "section_id": section_id,
                        "chapter": chapter["title"],
                        "title": section["title"],
                        "content": content,
                        "auto_generated": True,
                        "field_survey_required": section.get("field_survey_required", False),
                        "badge": self._get_badge(section),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "disclaimer": _DISCLAIMER,
                        "llm_generated": True,
                        "rag_referenced": bool(rag_reference),
                    }
        return None

    def get_template(self) -> dict:
        """평가서 템플릿 구조를 반환한다."""
        return self._template

    # ──────────────────────────────────────────────
    # 섹션별 초안 생성 (규칙 기반)
    # ──────────────────────────────────────────────

    def _generate_section_content(
        self,
        section_id: str,
        section_meta: dict,
        chapter_title: str,
        project_info: dict[str, Any],
        risk_cards: list[dict[str, Any]],
        regulations: list[dict[str, Any]],
        patterns: dict[str, Any],
    ) -> str:
        """섹션 ID에 따라 적절한 초안을 생성한다."""
        generators = {
            "ch1_s1": self._gen_purpose,
            "ch1_s2": self._gen_project_content,
            "ch1_s3": self._gen_legal_framework,
            "ch2_s1": self._gen_natural_env,
            "ch2_s2": self._gen_living_env,
            "ch2_s3": self._gen_social_env,
            "ch3_s1": self._gen_air_quality,
            "ch3_s2": self._gen_water_quality,
            "ch3_s3": self._gen_noise,
            "ch3_s4": self._gen_soil,
            "ch3_s5": self._gen_ecology,
            "ch3_s6": self._gen_landscape,
            "ch3_s7": self._gen_marine_env,
            "ch3_s8": self._gen_greenhouse,
            "ch3_s9": self._gen_odor,
            "ch4_s1": self._gen_construction_mitigation,
            "ch4_s2": self._gen_operation_mitigation,
            "ch5_s1": self._gen_comprehensive_assessment,
            "ch5_s2": self._gen_conclusion,
            "ch6_s1": self._gen_monitoring_plan,
            "ch6_s2": self._gen_monitoring_points,
            "ch7_s1": self._gen_alternatives,
        }

        generator = generators.get(section_id)
        if generator:
            return generator(project_info, risk_cards, regulations, patterns)

        return f"[{section_meta['title']}] 이 섹션의 초안 생성이 필요합니다."

    # ── Chapter 1: 사업의 개요 ──

    def _gen_purpose(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        name = project_info.get("project_name", "(사업명 미입력)")
        ptype = _TYPE_LABELS.get(project_info.get("project_type", ""), "기타")
        address = project_info.get("address", "(주소 미입력)")

        return (
            f"## 1.1 사업의 목적 및 필요성\n\n"
            f"본 사업 **{name}**은(는) {address} 일대에서 추진하는 **{ptype}** 사업으로, "
            f"지역 발전 및 기반시설 확충을 목적으로 한다.\n\n"
            f"해당 지역의 환경 여건을 고려하여 사업 추진에 따른 환경영향을 사전에 검토하고, "
            f"환경영향 최소화를 위한 저감 방안을 수립하기 위하여 환경영향평가를 실시한다.\n\n"
            f"> **[자동 생성]** 사업의 구체적 목적과 필요성은 사업 계획서를 참고하여 보완이 필요합니다."
        )

    def _gen_project_content(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        name = project_info.get("project_name", "(사업명)")
        ptype = _TYPE_LABELS.get(project_info.get("project_type", ""), "기타")
        scale = project_info.get("project_scale", "(규모 미입력)")
        address = project_info.get("address", "(주소 미입력)")

        return (
            f"## 1.2 사업의 내용\n\n"
            f"| 항목 | 내용 |\n"
            f"|------|------|\n"
            f"| 사업명 | {name} |\n"
            f"| 사업유형 | {ptype} |\n"
            f"| 사업규모 | {scale} |\n"
            f"| 사업위치 | {address} |\n"
            f"| 사업기간 | (사업 계획서 참조) |\n\n"
            f"> **[자동 생성]** 구체적인 공사 내용, 시설 배치, 토지이용 계획 등은 설계도서를 참고하여 보완이 필요합니다."
        )

    def _gen_legal_framework(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        lines = ["## 1.3 관련 법규 및 계획\n"]

        if regulations:
            lines.append("### 관련 법규\n")
            lines.append("| 규제명 | 법적 근거 | 인허가 필요 | 관련 기관 |")
            lines.append("|--------|----------|-----------|----------|")
            for reg in regulations[:10]:
                name = reg.get("regulation_name", "")
                basis = reg.get("legal_basis", "")
                permit = "필요" if reg.get("permit_required") else "-"
                authority = reg.get("related_authority", "-")
                lines.append(f"| {name} | {basis} | {permit} | {authority} |")
            lines.append("")

        if risk_cards:
            lines.append("### 주요 환경 리스크 요인\n")
            for card in risk_cards:
                severity = card.get("severity", "info")
                title = card.get("title", "")
                basis = card.get("legal_basis", "")
                severity_kr = {"critical": "심각", "major": "주요", "review": "검토", "info": "참고"}.get(severity, severity)
                lines.append(f"- **[{severity_kr}]** {title}")
                if basis:
                    lines.append(f"  - 법적 근거: {basis}")
            lines.append("")

        lines.append("> **[자동 생성]** 상위 계획 및 관련 개발 계획에 대한 검토가 추가로 필요합니다.")
        return "\n".join(lines)

    # ── Chapter 2: 지역 개황 ──

    def _gen_natural_env(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        address = project_info.get("address", "(주소)")
        eco_cards = [c for c in risk_cards if c.get("rule_id", "").startswith("ECO")]

        lines = [
            f"## 2.1 자연환경 현황\n",
            f"### 기후\n",
            f"{address} 일대는 대한민국 중부지방에 해당하며, "
            f"연평균 기온 약 12~13°C, 연평균 강수량 약 1,200~1,400mm로 추정된다.\n",
            f"> **[현장조사 필요]** 최근 5년간 기상 관측 데이터를 ASOS/AWS에서 수집하여 보완 필요\n",
            f"### 지형·지질\n",
            f"사업지 주변의 지형, 표고, 경사도는 수치지형도 분석을 통해 확인한다.\n",
            f"> **[현장조사 필요]** 정밀 지형측량 및 지질조사 필요\n",
        ]

        if eco_cards:
            lines.append("### 생태 관련 리스크 요인\n")
            for card in eco_cards:
                lines.append(f"- {card.get('title', '')}: {card.get('rationale', '')}")
            lines.append("")

        lines.append("> **[자동 생성]** 동식물상, 서식지 현황은 4계절 현장 생태조사 결과를 반영하여 보완합니다.")
        return "\n".join(lines)

    def _gen_living_env(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        env_cards = [
            c for c in risk_cards
            if any(c.get("rule_id", "").startswith(p) for p in ("AIR", "WAT", "NOI", "SOI"))
        ]

        lines = [
            "## 2.2 생활환경 현황\n",
            "### 대기질\n",
            "사업지 인근 에어코리아 측정소의 대기오염도를 기준으로 현황을 파악한다.\n",
            "> **[현장조사 필요]** PM10, PM2.5, NO2 등 주요 항목 실측 필요\n",
            "### 수질\n",
            "사업지 인근 수질측정망의 측정 결과를 기준으로 수질 현황을 파악한다.\n",
            "> **[현장조사 필요]** BOD, COD, SS, T-P 등 실측 필요\n",
            "### 소음·진동\n",
            "사업지 인근의 환경소음 현황을 파악한다.\n",
            "> **[현장조사 필요]** 주간/야간 환경소음 실측 필요\n",
        ]

        if env_cards:
            lines.append("### 식별된 환경 리스크\n")
            for card in env_cards:
                lines.append(f"- **{card.get('title', '')}**: {card.get('rationale', '')}")
            lines.append("")

        lines.append("> **[자동 생성]** 실측 데이터 확보 후 현황값을 갱신합니다.")
        return "\n".join(lines)

    def _gen_social_env(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        address = project_info.get("address", "(주소)")
        soc_cards = [c for c in risk_cards if c.get("rule_id", "").startswith("SOC")]

        lines = [
            "## 2.3 사회·경제 환경 현황\n",
            "### 인구·가구\n",
            f"{address} 일대의 인구 현황은 통계청 인구총조사 자료를 기준으로 한다.\n",
            "### 토지이용\n",
            "사업지 및 주변 지역의 용도지역·지구 현황을 토지이용규제정보서비스로 확인한다.\n",
            "### 교통\n",
            "사업지 인근 도로의 교통량 현황은 국가교통DB를 참조한다.\n",
        ]

        if soc_cards:
            lines.append("### 사회환경 관련 리스크\n")
            for card in soc_cards:
                lines.append(f"- {card.get('title', '')}: {card.get('rationale', '')}")
            lines.append("")

        lines.append("> **[자동 생성]** 문화재 현황, 주민 생활권 분석은 현장 확인 후 보완합니다.")
        return "\n".join(lines)

    # ── Chapter 3: 평가 항목별 현황 (with patterns) ──

    def _gen_assessment_section(
        self,
        title: str,
        domain_prefix: str,
        issue_keyword: str,
        project_info: dict,
        risk_cards: list,
        patterns: dict,
    ) -> str:
        """평가 항목 공통 생성기."""
        ptype_kr = patterns.get("korean_type", "기타")
        total = patterns.get("total_in_type", 0)
        predicted = patterns.get("predicted_issues", [])
        remediation = patterns.get("remediation_suggestions", [])

        relevant_issues = [
            i for i in predicted
            if issue_keyword in i.get("issue", "")
        ]
        relevant_remed = [
            r for r in remediation
            if issue_keyword in r.get("issue", "")
        ]
        domain_cards = [c for c in risk_cards if c.get("rule_id", "").startswith(domain_prefix)]

        lines = [f"## {title}\n"]

        lines.append("### 현황\n")
        lines.append("> **[현장조사 필요]** 현장 실측 데이터를 확보하여 현황을 기술합니다.\n")

        if domain_cards:
            lines.append("### 식별된 리스크\n")
            for card in domain_cards:
                sev_kr = {"critical": "심각", "major": "주요", "review": "검토", "info": "참고"}.get(card.get("severity", ""), "")
                lines.append(f"- **[{sev_kr}]** {card.get('title', '')}")
                lines.append(f"  - {card.get('rationale', '')}")
                if card.get("legal_basis"):
                    lines.append(f"  - 법적 근거: {card['legal_basis']}")
            lines.append("")

        if relevant_issues:
            lines.append("### 과거 패턴 분석\n")
            lines.append(f"과거 **{ptype_kr}** 사업 {total:,}건 분석 결과:\n")
            for issue in relevant_issues:
                lines.append(
                    f"- **{issue['issue']}**: {issue['probability_pct']}% "
                    f"({issue['past_count']:,}건/{total:,}건)"
                )
            lines.append("")

        lines.append("### 영향 예측\n")
        lines.append("> **[전문가 검토 필요]** 정밀 모델링 및 전문가 검토가 필요합니다.\n")

        if relevant_remed:
            lines.append("### 참고: 과거 저감 사례\n")
            for rem in relevant_remed:
                lines.append(f"**{rem['issue']}** (빈도 {rem['frequency']:.0%}):")
                for measure in rem.get("common_remediation", []):
                    lines.append(f"  - {measure}")
            lines.append("")

        lines.append(f"> **[자동 생성]** {_DISCLAIMER}")
        return "\n".join(lines)

    def _gen_air_quality(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.1 대기질", "AIR", "대기", project_info, risk_cards, patterns,
        )

    def _gen_water_quality(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.2 수질", "WAT", "수질", project_info, risk_cards, patterns,
        )

    def _gen_noise(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.3 소음·진동", "NOI", "소음", project_info, risk_cards, patterns,
        )

    def _gen_soil(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.4 토양·지하수", "SOI", "토양", project_info, risk_cards, patterns,
        )

    def _gen_ecology(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.5 생태계", "ECO", "생태", project_info, risk_cards, patterns,
        )

    def _gen_landscape(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return self._gen_assessment_section(
            "3.6 경관", "LAN", "경관", project_info, risk_cards, patterns,
        )

    def _gen_marine_env(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        """3.7 해양환경 — port, reclamation 유형에서 활성."""
        ptype = project_info.get("project_type", "")
        if ptype not in ("port", "reclamation", "river"):
            return (
                "## 3.7 해양환경\n\n"
                "본 사업유형은 해양환경 평가 대상이 아닙니다.\n\n"
                f"> **[자동 생성]** {_DISCLAIMER}"
            )
        return self._gen_assessment_section(
            "3.7 해양환경", "MAR", "해양", project_info, risk_cards, patterns,
        )

    def _gen_greenhouse(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        """3.8 온실가스 — energy 유형에서 중점."""
        ptype = project_info.get("project_type", "")
        if ptype not in ("energy", "industrial", "waste"):
            return (
                "## 3.8 온실가스\n\n"
                "본 사업유형은 온실가스 중점 평가 대상이 아닙니다. "
                "다만, 대규모 사업의 경우 온실가스 배출량 산정이 권고됩니다.\n\n"
                f"> **[자동 생성]** {_DISCLAIMER}"
            )
        return self._gen_assessment_section(
            "3.8 온실가스", "GHG", "온실가스", project_info, risk_cards, patterns,
        )

    def _gen_odor(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        """3.9 악취 — industrial, waste 유형에서 활성."""
        ptype = project_info.get("project_type", "")
        if ptype not in ("industrial", "waste", "reclamation"):
            return (
                "## 3.9 악취\n\n"
                "본 사업유형은 악취 중점 평가 대상이 아닙니다.\n\n"
                f"> **[자동 생성]** {_DISCLAIMER}"
            )
        return self._gen_assessment_section(
            "3.9 악취", "ODR", "악취", project_info, risk_cards, patterns,
        )

    # ── Chapter 4: 저감 방안 ──

    def _gen_construction_mitigation(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        remediation = patterns.get("remediation_suggestions", [])

        lines = [
            "## 4.1 공사 시 저감 방안\n",
            "공사 단계에서의 환경영향을 최소화하기 위한 저감 방안을 항목별로 제시한다.\n",
        ]

        if remediation:
            lines.append("### 과거 사례 기반 저감 방안\n")
            for rem in remediation:
                lines.append(f"**{rem['issue']}** (과거 적용 빈도 {rem['frequency']:.0%}):")
                for measure in rem.get("common_remediation", []):
                    lines.append(f"- {measure}")
                lines.append("")

        lines.extend([
            "### 공통 저감 방안\n",
            "- 비산먼지 억제: 살수차 운영, 세륜시설 설치",
            "- 소음·진동 관리: 공사시간 제한(06:00~22:00), 저소음 장비 사용",
            "- 수질 보호: 침사지 설치, 가배수로 설치",
            "- 비점오염원 관리: 임시 침전조 설치\n",
            f"> **[자동 생성]** {_DISCLAIMER}",
        ])

        return "\n".join(lines)

    def _gen_operation_mitigation(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        lines = [
            "## 4.2 운영 시 저감 방안\n",
            "운영 단계에서의 환경영향을 최소화하기 위한 저감 방안을 제시한다.\n",
        ]

        major_cards = [c for c in risk_cards if c.get("severity") in ("critical", "major")]
        if major_cards:
            lines.append("### 주요 리스크 대응 방안\n")
            for card in major_cards:
                lines.append(f"**{card.get('title', '')}**:")
                action = card.get("next_action", "")
                if action:
                    lines.append(f"- {action}")
                lines.append("")

        lines.extend([
            "### 일반 운영 관리\n",
            "- 주기적 환경모니터링 실시",
            "- 환경관리 매뉴얼 수립 및 교육",
            "- 민원 대응 체계 구축\n",
            f"> **[자동 생성]** {_DISCLAIMER}",
        ])

        return "\n".join(lines)

    # ── Chapter 5: 종합 평가 ──

    def _gen_comprehensive_assessment(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        name = project_info.get("project_name", "(사업명)")
        consultation = patterns.get("consultation_prediction", {})
        top_result = max(consultation.items(), key=lambda x: x[1]) if consultation else ("미정", 0)

        sev_counts = {"critical": 0, "major": 0, "review": 0, "info": 0}
        for card in risk_cards:
            sev = card.get("severity", "info")
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

        lines = [
            "## 5.1 환경영향 종합 평가\n",
            f"**{name}** 사업에 대한 환경영향을 종합적으로 평가한 결과는 다음과 같다.\n",
            "### 리스크 요약\n",
            f"| 심각도 | 건수 |",
            f"|--------|------|",
            f"| 심각 (Critical) | {sev_counts['critical']}건 |",
            f"| 주요 (Major) | {sev_counts['major']}건 |",
            f"| 검토 (Review) | {sev_counts['review']}건 |",
            f"| 참고 (Info) | {sev_counts['info']}건 |\n",
        ]

        if consultation:
            lines.append("### 과거 데이터 기반 협의결과 예측\n")
            for result, pct in sorted(consultation.items(), key=lambda x: -x[1]):
                if pct > 0:
                    lines.append(f"- {result}: {pct}%")
            lines.append(f"\n과거 유사 사업 통계에 따르면, **{top_result[0]}** ({top_result[1]}%)이 "
                         f"가장 높은 확률로 예측됩니다.\n")

        lines.append(f"> **[전문가 검토 필요]** {_DISCLAIMER}")
        return "\n".join(lines)

    def _gen_conclusion(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        name = project_info.get("project_name", "(사업명)")
        supplement_pct = patterns.get("supplement_required_pct")

        lines = [
            "## 5.2 결론 및 건의사항\n",
            f"**{name}** 사업은 환경영향평가를 통해 식별된 리스크 요인에 대하여 "
            f"적절한 저감 방안을 수립·이행함으로써 환경에 미치는 부정적 영향을 "
            f"최소화할 수 있을 것으로 판단된다.\n",
            "### 건의사항\n",
        ]

        major_cards = [c for c in risk_cards if c.get("severity") in ("critical", "major")]
        for i, card in enumerate(major_cards[:5], 1):
            lines.append(f"{i}. **{card.get('title', '')}**: {card.get('next_action', '조치 필요')}")

        if supplement_pct is not None:
            lines.append(
                f"\n> 참고: 유사 사업의 보완 요구 확률은 {supplement_pct}%입니다. "
                f"사전에 충분한 검토를 권장합니다."
            )

        lines.append(f"\n> **[전문가 검토 필요]** {_DISCLAIMER}")
        return "\n".join(lines)

    # ── Chapter 6: 사후 모니터링 ──

    def _gen_monitoring_plan(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        predicted = patterns.get("predicted_issues", [])
        top_issues = [i["issue"] for i in predicted[:5]] if predicted else []

        lines = [
            "## 6.1 조사 항목 및 방법\n",
            "사후환경영향조사는 환경영향평가서에서 예측된 영향을 검증하고, "
            "저감 방안의 이행 여부를 확인하기 위하여 실시한다.\n",
            "### 조사 항목\n",
            "| 항목 | 조사 주기 | 비고 |",
            "|------|----------|------|",
            "| 대기질 | 분기 1회 | PM10, PM2.5, NO2 |",
            "| 수질 | 분기 1회 | BOD, COD, SS, T-P |",
            "| 소음·진동 | 분기 1회 | 주간/야간 |",
            "| 생태계 | 반기 1회 | 동식물상, 서식지 |",
        ]

        if top_issues:
            lines.append("\n### 중점 모니터링 항목 (과거 빈출 기반)\n")
            for issue in top_issues:
                lines.append(f"- {issue}")

        lines.append(f"\n> **[자동 생성]** {_DISCLAIMER}")
        return "\n".join(lines)

    def _gen_monitoring_points(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        return (
            "## 6.2 조사 지점 및 주기\n\n"
            "> **[전문가 검토 필요]** 조사 지점 및 주기는 사업지의 현장 여건, "
            "주변 민감 수용체 위치, 기존 측정망과의 관계 등을 종합적으로 고려하여 "
            "전문가가 설정하여야 합니다.\n\n"
            "본 섹션은 자동 생성이 불가능하며, 현장조사 결과를 반영하여 작성합니다.\n\n"
            f"> {_DISCLAIMER}"
        )

    # ── Chapter 7: 대안 검토 ──

    def _gen_alternatives(
        self, project_info: dict, risk_cards: list, regulations: list, patterns: dict,
    ) -> str:
        """7.1 대안 설정 및 비교 분석."""
        name = project_info.get("project_name", "(사업명)")
        critical_cards = [c for c in risk_cards if c.get("severity") == "critical"]

        lines = [
            "## 7.1 대안 설정 및 비교 분석\n",
            f"**{name}** 사업의 환경영향을 최소화하기 위하여 다음과 같은 대안을 검토한다.\n",
            "### 대안의 종류\n",
            "| 구분 | 내용 |",
            "|------|------|",
            "| 부지 대안 | 사업지 대안 위치 검토 (입지 리스크 비교) |",
            "| 규모 대안 | 사업 규모 조정에 따른 환경영향 변화 |",
            "| 공법 대안 | 환경친화적 공법 적용 가능성 검토 |",
            "| 무사업 대안 | 사업 미시행 시 환경 변화 예측 |\n",
        ]

        if critical_cards:
            lines.append("### Critical 리스크 기반 대안 검토 필요 사항\n")
            for card in critical_cards:
                lines.append(f"- **{card.get('title', '')}**: 부지 대안 또는 공법 대안 검토 필요")
                if card.get("next_action"):
                    lines.append(f"  - 권고 조치: {card['next_action']}")
            lines.append("")

        lines.extend([
            "### 대안 비교 방법\n",
            "환경성, 경제성, 기술성을 종합적으로 비교 평가하며, "
            "EIA Pre-Screen의 부지 비교 기능을 활용하여 입지별 리스크를 정량 비교할 수 있다.\n",
            "> **[전문가 검토 필요]** 대안 설정의 합리성과 비교 평가 결과는 전문가가 검증해야 합니다.\n",
            f"> **[자동 생성]** {_DISCLAIMER}",
        ])

        return "\n".join(lines)

    # ──────────────────────────────────────────────
    # LLM 호출
    # ──────────────────────────────────────────────

    async def _get_rag_reference(
        self,
        section_title: str,
        project_type: str,
        risk_cards: list[dict[str, Any]],
    ) -> str:
        """RAG로 실제 평가서 참조 텍스트를 가져온다."""
        try:
            result = await self._rag.draft_assist(
                section_topic=section_title,
                project_type=project_type,
                risk_cards=risk_cards,
            )
            if result.get("available") and result.get("reference_text"):
                return result["reference_text"]
        except Exception as exc:
            logger.debug("RAG 참조 조회 실패: %s", exc)
        return ""

    def _build_llm_prompt(
        self,
        section_meta: dict,
        chapter_title: str,
        project_info: dict[str, Any],
        risk_cards: list[dict[str, Any]],
        regulations: list[dict[str, Any]],
        patterns: dict[str, Any],
        rag_reference: str = "",
    ) -> str:
        """LLM 프롬프트를 구성한다."""
        name = project_info.get("project_name", "(사업명)")
        ptype = _TYPE_LABELS.get(project_info.get("project_type", ""), "기타")
        scale = project_info.get("project_scale", "(규모)")
        address = project_info.get("address", "(주소)")

        prompt_parts = [
            f"환경영향평가서의 '{chapter_title}' > '{section_meta['title']}' 섹션을 작성해 주세요.\n",
            f"## 사업 정보",
            f"- 사업명: {name}",
            f"- 사업유형: {ptype}",
            f"- 사업규모: {scale}",
            f"- 사업위치: {address}\n",
        ]

        if risk_cards:
            prompt_parts.append("## 식별된 리스크")
            for card in risk_cards[:5]:
                prompt_parts.append(f"- [{card.get('severity')}] {card.get('title')}: {card.get('rationale')}")
            prompt_parts.append("")

        if regulations:
            prompt_parts.append("## 관련 규제")
            for reg in regulations[:5]:
                prompt_parts.append(f"- {reg.get('regulation_name')}: {reg.get('legal_basis')}")
            prompt_parts.append("")

        predicted = patterns.get("predicted_issues", [])
        if predicted:
            prompt_parts.append("## 과거 패턴")
            for issue in predicted[:5]:
                prompt_parts.append(f"- {issue['issue']}: {issue['probability_pct']}%")
            prompt_parts.append("")

        if rag_reference:
            prompt_parts.append("## 유사 사업유형의 실제 평가서 참조")
            prompt_parts.append("아래는 유사한 사업유형의 실제 환경영향평가서에서 발췌한 내용입니다. ")
            prompt_parts.append("이를 참고하여 작성하되, 출처를 명시해 주세요.\n")
            prompt_parts.append(rag_reference)
            prompt_parts.append("")

        prompt_parts.extend([
            "## 작성 지침",
            "- 마크다운 형식으로 작성",
            "- 전문적이지만 이해하기 쉬운 한국어 사용",
            "- 현장조사가 필요한 부분은 '[현장조사 필요]' 표시",
            "- 전문가 검토가 필요한 부분은 '[전문가 검토 필요]' 표시",
            f"- 섹션 설명: {section_meta.get('description', '')}",
        ])

        if rag_reference:
            prompt_parts.append("- 실제 평가서 참조 내용이 있는 경우 '유사 사업유형의 실제 평가서에서는 이렇게 기술했습니다: ...' 형태로 인용")

        return "\n".join(prompt_parts)

    async def _call_llm(self, prompt: str) -> str:
        """OpenRouter API를 통해 DeepSeek을 호출한다."""
        try:
            client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 대한민국 환경영향평가서 작성 전문가입니다. "
                            "평가서 각 섹션의 초안을 전문적이고 체계적으로 작성합니다. "
                            f"중요: {_DISCLAIMER}"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("Draft LLM 호출 실패: %s", exc)
            return f"[LLM 호출 실패] {exc}\n\n규칙 기반 초안으로 대체합니다."

    # ──────────────────────────────────────────────
    # 유틸
    # ──────────────────────────────────────────────

    @staticmethod
    def _get_badge(section: dict) -> str:
        """섹션 상태 배지를 반환한다."""
        if not section.get("auto_generable", False):
            return "전문가 검토 필요"
        if section.get("field_survey_required", False):
            return "현장조사 필요"
        return "자동 생성"
