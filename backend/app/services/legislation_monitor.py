"""법령 개정 모니터링 서비스.

6개 주요 법령의 최종 개정일을 추적하고,
시스템에 반영된 버전과 비교하여 개정 여부를 판단한다.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.connectors.legislation import LegislationConnector, MONITORED_LAWS

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_LAW_VERSIONS_PATH = _DATA_DIR / "law_versions.json"


class LawStatus:
    """단일 법령의 상태."""

    def __init__(
        self,
        law_name: str,
        system_version: str,
        last_amendment: str | None = None,
        checked_at: str | None = None,
        acknowledged: bool = False,
    ):
        self.law_name = law_name
        self.system_version = system_version
        self.last_amendment = last_amendment
        self.checked_at = checked_at
        self.acknowledged = acknowledged

    @property
    def is_outdated(self) -> bool:
        """시스템 버전보다 최신 개정이 있으면 True."""
        if not self.last_amendment or not self.system_version:
            return False
        try:
            return str(self.last_amendment) > str(self.system_version)
        except (TypeError, ValueError):
            return False

    def to_dict(self) -> dict:
        return {
            "law_name": self.law_name,
            "system_version": self.system_version,
            "last_amendment": self.last_amendment,
            "checked_at": self.checked_at,
            "is_outdated": self.is_outdated,
            "acknowledged": self.acknowledged,
        }


# 시스템에 반영된 법령 버전 기준일 (규칙 YAML 작성 기준)
_DEFAULT_SYSTEM_VERSIONS: dict[str, str] = {
    "환경영향평가법": "20250218",
    "환경영향평가법 시행령": "20250218",
    "자연환경보전법": "20250218",
    "국토의 계획 및 이용에 관한 법률": "20250218",
    "농지법": "20250218",
    "습지보전법": "20250218",
}


class LegislationMonitor:
    """법령 개정 모니터링 서비스."""

    def __init__(self) -> None:
        self._connector = LegislationConnector()
        self._versions: dict[str, dict] = self._load_versions()

    def _load_versions(self) -> dict[str, dict]:
        """저장된 법령 버전 정보를 로드한다."""
        if _LAW_VERSIONS_PATH.exists():
            try:
                return json.loads(_LAW_VERSIONS_PATH.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("법령 버전 파일 로드 실패: %s", e)

        # 기본값 생성
        versions = {}
        for law in MONITORED_LAWS:
            name = law["name"]
            versions[name] = {
                "system_version": _DEFAULT_SYSTEM_VERSIONS.get(name, "20250218"),
                "last_amendment": None,
                "checked_at": None,
                "acknowledged": False,
            }
        return versions

    def _save_versions(self) -> None:
        """법령 버전 정보를 파일에 저장한다."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _LAW_VERSIONS_PATH.write_text(
            json.dumps(self._versions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def check_all(self) -> list[dict]:
        """모든 모니터링 법령의 최신 개정일을 조회한다."""
        result = await self._connector.fetch()
        now = datetime.now(timezone.utc).isoformat()

        statuses: list[dict] = []
        if result.data:
            for law_name, info in result.data.items():
                amendment = info.get("last_amendment")
                if law_name not in self._versions:
                    self._versions[law_name] = {
                        "system_version": _DEFAULT_SYSTEM_VERSIONS.get(law_name, "20250218"),
                        "last_amendment": None,
                        "checked_at": None,
                        "acknowledged": False,
                    }

                self._versions[law_name]["last_amendment"] = amendment
                self._versions[law_name]["checked_at"] = now

                status = LawStatus(
                    law_name=law_name,
                    system_version=self._versions[law_name]["system_version"],
                    last_amendment=amendment,
                    checked_at=now,
                    acknowledged=self._versions[law_name].get("acknowledged", False),
                )
                statuses.append(status.to_dict())

        self._save_versions()
        return statuses

    def get_status(self) -> list[dict]:
        """현재 저장된 법령 상태를 반환한다 (API 호출 없이)."""
        statuses = []
        for law_name, info in self._versions.items():
            status = LawStatus(
                law_name=law_name,
                system_version=info.get("system_version", ""),
                last_amendment=info.get("last_amendment"),
                checked_at=info.get("checked_at"),
                acknowledged=info.get("acknowledged", False),
            )
            statuses.append(status.to_dict())
        return statuses

    def acknowledge(self, law_name: str) -> bool:
        """관리자가 법령 개정을 확인 처리한다."""
        if law_name in self._versions:
            amendment = self._versions[law_name].get("last_amendment")
            if amendment:
                self._versions[law_name]["system_version"] = amendment
            self._versions[law_name]["acknowledged"] = True
            self._save_versions()
            return True
        return False
