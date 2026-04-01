"""법령정보 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스: 국가법령정보센터 Open API (open.law.go.kr)
법령명으로 검색 → 최종 개정일(시행일) 반환
"""

import logging
from typing import Any

import httpx

from backend.app.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    DataTier,
)
from backend.app.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# 모니터링 대상 6개 법령
MONITORED_LAWS: list[dict[str, str]] = [
    {"name": "환경영향평가법", "id": ""},
    {"name": "환경영향평가법 시행령", "id": ""},
    {"name": "자연환경보전법", "id": ""},
    {"name": "국토의 계획 및 이용에 관한 법률", "id": ""},
    {"name": "농지법", "id": ""},
    {"name": "습지보전법", "id": ""},
]


class LegislationConnector(BaseConnector):
    name = "legislation"
    tier = DataTier.B
    description = "국가법령정보센터 — 법령 개정일 모니터링"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float = 0,
        lat: float = 0,
        buffer_m: float = 0,
        **kwargs: Any,
    ) -> ConnectorResult:
        """모든 모니터링 대상 법령의 최종 개정일을 조회한다."""
        results: dict[str, dict] = {}

        async with httpx.AsyncClient(timeout=15) as client:
            for law in MONITORED_LAWS:
                law_name = law["name"]
                try:
                    info = await self._fetch_law_info(client, law_name)
                    results[law_name] = info
                except Exception as e:
                    logger.warning("법령 조회 실패 (%s): %s", law_name, e)
                    results[law_name] = {
                        "law_name": law_name,
                        "last_amendment": None,
                        "enforcement_date": None,
                        "error": str(e),
                    }

        self._cache.save_snapshot(self.name, "all", results)
        return self._make_result(results)

    async def _fetch_law_info(
        self, client: httpx.AsyncClient, law_name: str,
    ) -> dict:
        """국가법령정보센터 API로 법령 정보 조회."""
        try:
            resp = await client.get(
                "https://www.law.go.kr/DRF/lawSearch.do",
                params={
                    "OC": "chetera",
                    "target": "law",
                    "type": "JSON",
                    "query": law_name,
                    "display": "1",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("LawSearch", {}).get("law", [])
                if isinstance(items, dict):
                    items = [items]
                if items:
                    item = items[0]
                    return {
                        "law_name": law_name,
                        "official_name": item.get("법령명한글", law_name),
                        "last_amendment": item.get("시행일자", None),
                        "enforcement_date": item.get("시행일자", None),
                        "law_id": item.get("법령일련번호", ""),
                    }
        except Exception as e:
            logger.debug("Law API parse error for %s: %s", law_name, e)

        return {
            "law_name": law_name,
            "last_amendment": None,
            "enforcement_date": None,
        }

    async def fetch_single(self, law_name: str) -> dict:
        """단일 법령의 최종 개정일을 조회한다."""
        async with httpx.AsyncClient(timeout=10) as client:
            return await self._fetch_law_info(client, law_name)
