"""DeepSeek V3 (via OpenRouter) LLM 해석 서비스.

리스크 카드와 규제 매칭 결과를 자연어(한국어)로 해석하여 반환한다.
OpenAI SDK를 사용하며, OpenRouter를 통해 DeepSeek V3 모델을 호출한다.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from openai import AsyncOpenAI

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_DISCLAIMER = "이 해석은 참고용이며 법적 효력이 없습니다"

_SYSTEM_PROMPT = f"""\
당신은 대한민국 환경영향평가(EIA) 사전 스크리닝 전문 분석가입니다.
사용자에게 리스크 평가 결과와 관련 규제 정보를 바탕으로,
사업 추진 시 고려해야 할 환경 리스크를 명확하고 이해하기 쉬운 한국어로 해석해 주세요.

응답 지침:
- 2~3개 문단으로 작성하세요.
- 첫 문단: 전체적인 리스크 수준과 핵심 위험 요인을 요약합니다.
- 둘째 문단: 관련 규제와 법적 근거를 설명하고, 필요한 인허가 절차를 안내합니다.
- 셋째 문단(선택): 권고 사항 및 다음 단계를 제시합니다.
- 전문 용어를 사용할 때는 괄호 안에 간단한 설명을 추가하세요.
- 심각도(severity)가 높은 항목을 우선적으로 다루세요.

중요 고지: {_DISCLAIMER}
"""


class LLMInterpreter:
    """OpenRouter + DeepSeek V3를 사용한 리스크 해석 서비스."""

    def __init__(self) -> None:
        self._model = settings.LLM_MODEL

    async def interpret(
        self,
        risk_cards: list[dict[str, Any]],
        regulation_matches: list[dict[str, Any]],
        data_status: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """리스크 카드와 규제 매칭 결과를 자연어로 해석한다.

        Args:
            risk_cards: 리스크 엔진이 생성한 리스크 카드 목록.
            regulation_matches: 규제 매칭 결과 목록.
            data_status: 데이터 수집 상태 정보 (선택).

        Returns:
            해석 결과 딕셔너리:
                - interpretation: 자연어 해석 텍스트
                - model: 사용된 모델명
                - generated_at: 생성 시각 (ISO 8601)
                - disclaimer: 법적 고지 문구
                - ai_generated: AI 생성 여부 라벨
        """
        # ── API 키 검증 ──
        if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_API_KEY.strip():
            logger.error("OPENROUTER_API_KEY가 설정되지 않았습니다.")
            return self._error_response(
                "LLM 해석을 수행할 수 없습니다: OPENROUTER_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 유효한 API 키를 설정해 주세요."
            )

        # ── 프롬프트 구성 ──
        user_prompt = self._build_prompt(risk_cards, regulation_matches, data_status)

        # ── OpenRouter API 호출 ──
        try:
            client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            interpretation_text = response.choices[0].message.content
        except Exception as exc:
            logger.exception("OpenRouter API 호출 중 오류 발생: %s", exc)
            return self._error_response(
                f"LLM 해석 중 오류가 발생했습니다: {exc}. "
                "잠시 후 다시 시도해 주세요."
            )

        return {
            "interpretation": interpretation_text,
            "model": self._model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
            "ai_generated": "AI 생성",
        }

    # ──────────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────────

    def _build_prompt(
        self,
        risk_cards: list[dict[str, Any]],
        regulation_matches: list[dict[str, Any]],
        data_status: Optional[dict[str, Any]] = None,
    ) -> str:
        """리스크 카드, 규제 매칭, 데이터 상태를 구조화된 프롬프트로 변환한다."""
        sections: list[str] = []

        # ── 리스크 카드 섹션 ──
        sections.append("## 리스크 평가 결과")
        if not risk_cards:
            sections.append("식별된 리스크가 없습니다.")
        else:
            sections.append(f"총 {len(risk_cards)}건의 리스크가 식별되었습니다.\n")
            for i, card in enumerate(risk_cards, 1):
                sections.append(self._format_risk_card(i, card))

        sections.append("")

        # ── 규제 매칭 섹션 ──
        sections.append("## 관련 규제 매칭 결과")
        if not regulation_matches:
            sections.append("매칭된 규제가 없습니다.")
        else:
            sections.append(
                f"총 {len(regulation_matches)}건의 관련 규제가 확인되었습니다.\n"
            )
            for i, reg in enumerate(regulation_matches, 1):
                sections.append(self._format_regulation(i, reg))

        # ── 데이터 상태 섹션 (선택) ──
        if data_status:
            sections.append("")
            sections.append("## 데이터 수집 상태")
            for key, value in data_status.items():
                sections.append(f"- {key}: {value}")

        sections.append("")
        sections.append(
            "위 정보를 바탕으로 사업 추진 시 고려해야 할 환경 리스크를 "
            "2~3개 문단으로 해석해 주세요."
        )

        return "\n".join(sections)

    @staticmethod
    def _format_risk_card(index: int, card: dict[str, Any]) -> str:
        """단일 리스크 카드를 텍스트로 포맷한다."""
        rule_id = card.get("rule_id", "N/A")
        title = card.get("title", "제목 없음")
        severity = card.get("severity", "N/A")
        rationale = card.get("rationale", "")
        evidence = card.get("evidence", "")
        next_action = card.get("next_action", "")
        legal_basis = card.get("legal_basis", "")

        lines = [
            f"### 리스크 {index}: {title}",
            f"- 규칙 ID: {rule_id}",
            f"- 심각도: {severity}",
        ]
        if rationale:
            lines.append(f"- 판단 근거: {rationale}")
        if evidence:
            lines.append(f"- 증거: {evidence}")
        if next_action:
            lines.append(f"- 권고 조치: {next_action}")
        if legal_basis:
            lines.append(f"- 법적 근거: {legal_basis}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_regulation(index: int, reg: dict[str, Any]) -> str:
        """단일 규제 매칭 항목을 텍스트로 포맷한다."""
        name = reg.get("regulation_name", "규제명 없음")
        code = reg.get("regulation_code", "")
        legal_basis = reg.get("legal_basis", "")
        description = reg.get("description", "")
        restriction_level = reg.get("restriction_level", "")
        permit_required = reg.get("permit_required", None)
        authority = reg.get("related_authority", "")

        lines = [
            f"### 규제 {index}: {name}",
        ]
        if code:
            lines.append(f"- 규제 코드: {code}")
        if legal_basis:
            lines.append(f"- 법적 근거: {legal_basis}")
        if description:
            lines.append(f"- 설명: {description}")
        if restriction_level:
            lines.append(f"- 규제 수준: {restriction_level}")
        if permit_required is not None:
            lines.append(f"- 인허가 필요: {'예' if permit_required else '아니오'}")
        if authority:
            lines.append(f"- 관련 기관: {authority}")
        lines.append("")
        return "\n".join(lines)

    def _error_response(self, message: str) -> dict[str, Any]:
        """오류 발생 시 일관된 응답 딕셔너리를 반환한다."""
        return {
            "interpretation": message,
            "model": self._model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
            "ai_generated": "AI 생성",
        }
