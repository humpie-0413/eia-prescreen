"""관리자 API — 법령 모니터링 + 규칙 관리.

C-1: 법령 개정 감지 (GET /law-status, POST /law-check, POST /law-acknowledge)
C-2: 규칙 CRUD (GET /rules, GET /rules/{id}, PUT /rules/{id})
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.core.auth import get_auth_user
from backend.app.services.legislation_monitor import LegislationMonitor
from backend.app.services.risk_engine import RiskEngine, RULES_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_RULE_CHANGES_PATH = _DATA_DIR / "rule_changes.jsonl"

# ── 의존성 ──


def _require_admin(user: dict = Depends(get_auth_user)) -> dict:
    """admin 역할만 접근 허용."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return user


# ── C-1: 법령 모니터링 ──


_monitor = LegislationMonitor()


@router.get("/law-status")
async def get_law_status(user: dict = Depends(get_auth_user)) -> dict:
    """6개 법령의 현재 상태를 반환한다."""
    statuses = _monitor.get_status()
    has_outdated = any(s.get("is_outdated") and not s.get("acknowledged") for s in statuses)
    return {
        "laws": statuses,
        "has_outdated": has_outdated,
        "total": len(statuses),
    }


@router.post("/law-check")
async def check_laws(user: dict = Depends(_require_admin)) -> dict:
    """수동으로 법령 개정 여부를 체크한다."""
    statuses = await _monitor.check_all()
    has_outdated = any(s.get("is_outdated") and not s.get("acknowledged") for s in statuses)
    return {
        "laws": statuses,
        "has_outdated": has_outdated,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class AcknowledgeRequest(BaseModel):
    law_name: str


@router.post("/law-acknowledge/{law_name}")
async def acknowledge_law(
    law_name: str,
    user: dict = Depends(_require_admin),
) -> dict:
    """관리자가 법령 개정을 확인 처리한다."""
    success = _monitor.acknowledge(law_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"법령 '{law_name}'을(를) 찾을 수 없습니다.")
    return {"status": "acknowledged", "law_name": law_name}


# ── C-2: 규칙 관리 ──


def _load_all_rules() -> list[dict]:
    """모든 YAML 규칙을 파일에서 로드하여 dict 목록으로 반환."""
    all_rules: list[dict] = []
    for yaml_path in sorted(RULES_DIR.glob("*.yaml")):
        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            domain = data.get("domain", yaml_path.stem)
            for rule in data.get("rules", []):
                rule["_domain"] = domain
                rule["_file"] = yaml_path.name
                all_rules.append(rule)
        except Exception as e:
            logger.warning("규칙 로드 실패 (%s): %s", yaml_path.name, e)
    return all_rules


def _load_yaml_file(filename: str) -> dict:
    """단일 YAML 파일을 로드한다."""
    path = RULES_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"파일 {filename}을 찾을 수 없습니다.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save_yaml_file(filename: str, data: dict) -> None:
    """YAML 파일을 저장한다."""
    path = RULES_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


@router.get("/rules")
async def list_rules(
    domain: str | None = None,
    user: dict = Depends(get_auth_user),
) -> dict:
    """전체 규칙 목록 (도메인별 그룹)."""
    all_rules = _load_all_rules()

    if domain:
        all_rules = [r for r in all_rules if r.get("_domain") == domain]

    # 도메인별 그룹화
    by_domain: dict[str, list[dict]] = {}
    for rule in all_rules:
        d = rule.get("_domain", "unknown")
        by_domain.setdefault(d, []).append({
            "rule_id": rule.get("rule_id"),
            "title": rule.get("title"),
            "severity": rule.get("severity"),
            "confidence": rule.get("confidence"),
            "human_review_required": rule.get("human_review_required"),
            "legal_basis": rule.get("legal_basis"),
            "domain": d,
            "condition": rule.get("condition"),
        })

    return {
        "total": len(all_rules),
        "domains": list(by_domain.keys()),
        "rules_by_domain": by_domain,
        "rules": [
            {
                "rule_id": r.get("rule_id"),
                "title": r.get("title"),
                "severity": r.get("severity"),
                "confidence": r.get("confidence"),
                "domain": r.get("_domain"),
            }
            for r in all_rules
        ],
    }


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: str,
    user: dict = Depends(get_auth_user),
) -> dict:
    """규칙 상세 (YAML 원문 포함)."""
    all_rules = _load_all_rules()
    for rule in all_rules:
        if rule.get("rule_id") == rule_id:
            return {
                "rule": rule,
                "yaml_source": yaml.dump(
                    {k: v for k, v in rule.items() if not k.startswith("_")},
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                ),
            }
    raise HTTPException(status_code=404, detail=f"규칙 {rule_id}을(를) 찾을 수 없습니다.")


class RuleUpdateRequest(BaseModel):
    severity: str | None = None
    confidence: float | None = None
    condition_value: Any | None = None
    human_review_required: bool | None = None


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    body: RuleUpdateRequest,
    user: dict = Depends(_require_admin),
) -> dict:
    """규칙 수정 (심각도, 신뢰도, 임계값, 전문가검토)."""
    # 해당 규칙이 있는 YAML 파일 찾기
    for yaml_path in sorted(RULES_DIR.glob("*.yaml")):
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        for i, rule in enumerate(rules):
            if rule.get("rule_id") == rule_id:
                changes: dict[str, Any] = {}

                if body.severity is not None:
                    changes["severity"] = (rule.get("severity"), body.severity)
                    rules[i]["severity"] = body.severity

                if body.confidence is not None:
                    changes["confidence"] = (rule.get("confidence"), body.confidence)
                    rules[i]["confidence"] = body.confidence

                if body.condition_value is not None:
                    old_val = rule.get("condition", {}).get("value")
                    changes["condition_value"] = (old_val, body.condition_value)
                    rules[i]["condition"]["value"] = body.condition_value

                if body.human_review_required is not None:
                    changes["human_review_required"] = (
                        rule.get("human_review_required"),
                        body.human_review_required,
                    )
                    rules[i]["human_review_required"] = body.human_review_required

                if not changes:
                    raise HTTPException(status_code=400, detail="변경 사항이 없습니다.")

                # YAML 저장
                data["rules"] = rules
                _save_yaml_file(yaml_path.name, data)

                # 변경 이력 기록
                _log_rule_change(rule_id, changes, user.get("user_id", ""))

                return {
                    "status": "updated",
                    "rule_id": rule_id,
                    "changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
                }

    raise HTTPException(status_code=404, detail=f"규칙 {rule_id}을(를) 찾을 수 없습니다.")


def _log_rule_change(rule_id: str, changes: dict, user_id: str) -> None:
    """규칙 변경 이력을 JSONL 파일에 기록한다."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule_id": rule_id,
        "user_id": user_id,
        "changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
    }
    with open(_RULE_CHANGES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
