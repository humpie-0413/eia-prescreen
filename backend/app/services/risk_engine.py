import logging
import operator as op
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel

from backend.app.rules.schema import RuleCondition, RuleDefinition, RuleSet

logger = logging.getLogger(__name__)

RULES_DIR = Path(__file__).resolve().parent.parent / "rules" / "v1"

# 연산자 매핑
_OPERATORS = {
    "eq": op.eq,
    "ne": op.ne,
    "gt": op.gt,
    "gte": op.ge,
    "lt": op.lt,
    "lte": op.le,
}


class RiskCardResult(BaseModel):
    """룰 엔진이 생성하는 리스크 카드 결과."""

    rule_id: str
    rule_version: str
    title: str
    severity: str
    rationale: str
    evidence: dict
    next_action: str
    legal_basis: Optional[str] = None
    confidence: float
    human_review_required: bool
    trigger_dataset: str
    source_snapshot_date: Optional[datetime] = None
    matched_value: Any = None


class RiskEngine:
    """YAML 규칙 기반 리스크 평가 엔진."""

    def __init__(self, rules_dir: Path = RULES_DIR) -> None:
        self._rules_dir = rules_dir
        self._rule_sets: list[RuleSet] = []
        self._rules: list[RuleDefinition] = []

    def load_rules(self) -> int:
        """YAML 파일에서 규칙을 로드한다. 로드된 규칙 수를 반환."""
        self._rule_sets = []
        self._rules = []

        if not self._rules_dir.exists():
            logger.warning("Rules directory not found: %s", self._rules_dir)
            return 0

        for yaml_path in sorted(self._rules_dir.glob("*.yaml")):
            try:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                rule_set = RuleSet(**data)
                self._rule_sets.append(rule_set)
                self._rules.extend(rule_set.rules)
                logger.info(
                    "Loaded %d rules from %s", len(rule_set.rules), yaml_path.name,
                )
            except Exception:
                logger.exception("Failed to load rules from %s", yaml_path.name)

        logger.info("Total rules loaded: %d", len(self._rules))
        return len(self._rules)

    @property
    def rules(self) -> list[RuleDefinition]:
        return self._rules

    @property
    def rule_sets(self) -> list[RuleSet]:
        return self._rule_sets

    def evaluate(
        self,
        screening_input: dict,
        spatial_data: dict,
    ) -> list[RiskCardResult]:
        """
        screening_input과 spatial_data를 기반으로 모든 규칙을 평가한다.

        Args:
            screening_input: 사업 입력 정보 (project_type, location 등)
            spatial_data: 공간 분석 결과 (커넥터에서 수집한 데이터)

        Returns:
            매칭된 리스크 카드 목록
        """
        if not self._rules:
            self.load_rules()

        results: list[RiskCardResult] = []
        merged = {**screening_input, **spatial_data}

        for rule in self._rules:
            matched, matched_value = self._evaluate_condition(rule.condition, merged)
            if matched:
                results.append(
                    RiskCardResult(
                        rule_id=rule.rule_id,
                        rule_version=rule.rule_version,
                        title=rule.title,
                        severity=rule.severity,
                        rationale=rule.rationale,
                        evidence={
                            "source": rule.evidence,
                            "trigger_dataset": rule.trigger_dataset,
                            "matched_value": matched_value,
                        },
                        next_action=rule.next_action,
                        legal_basis=rule.legal_basis,
                        confidence=rule.confidence,
                        human_review_required=rule.human_review_required,
                        trigger_dataset=rule.trigger_dataset,
                        source_snapshot_date=(
                            datetime.combine(rule.source_snapshot_date, datetime.min.time())
                            if rule.source_snapshot_date
                            else None
                        ),
                        matched_value=matched_value,
                    )
                )

        # severity 순 정렬: critical > major > review > info
        severity_order = {"critical": 0, "major": 1, "review": 2, "info": 3}
        results.sort(key=lambda r: severity_order.get(r.severity, 99))

        return results

    def _evaluate_condition(
        self,
        condition: RuleCondition,
        data: dict,
    ) -> tuple[bool, Any]:
        """개별 조건을 평가한다. (매칭 여부, 매칭된 값) 반환."""
        field_value = self._resolve_field(condition.field, data)

        # exists / not_exists
        if condition.operator == "exists":
            return (field_value is not None, field_value)
        if condition.operator == "not_exists":
            return (field_value is None, None)

        if field_value is None:
            return (False, None)

        # 비교 연산
        if condition.operator in _OPERATORS:
            try:
                return (
                    _OPERATORS[condition.operator](field_value, condition.value),
                    field_value,
                )
            except TypeError:
                return (False, field_value)

        # in / not_in
        if condition.operator == "in":
            return (field_value in condition.value, field_value)
        if condition.operator == "not_in":
            return (field_value not in condition.value, field_value)

        # contains / not_contains (리스트 또는 문자열)
        if condition.operator == "contains":
            if isinstance(field_value, (list, set)):
                return (condition.value in field_value, field_value)
            return (str(condition.value) in str(field_value), field_value)
        if condition.operator == "not_contains":
            if isinstance(field_value, (list, set)):
                return (condition.value not in field_value, field_value)
            return (str(condition.value) not in str(field_value), field_value)

        # intersects: 공간 데이터에서 중첩 여부 (bool 필드)
        if condition.operator == "intersects":
            return (bool(field_value), field_value)

        # within_buffer: 버퍼 거리 이내 (distance_m <= value)
        if condition.operator == "within_buffer":
            try:
                return (float(field_value) <= float(condition.value), field_value)
            except (TypeError, ValueError):
                return (False, field_value)

        logger.warning("Unknown operator: %s", condition.operator)
        return (False, None)

    def _resolve_field(self, field: str, data: dict) -> Any:
        """점(.) 표기법으로 중첩 딕셔너리 필드에 접근."""
        parts = field.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current
