"""해양환경 커넥터 (B계층 — 불안정형 + 캐시).

데이터 소스:
- 1차: 1480523 환평 해양환경서비스 (MaritimeService/getIvstg) — mgtNo 필수
- 2차: 1192000 해양수산부 환경영향평가 (EnvImpactService)
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
from backend.app.core.config import settings
from backend.app.services.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class MarineConnector(BaseConnector):
    name = "marine"
    tier = DataTier.B
    description = "EIASS 해양환경정보 — 해양생태계·연안·어장"

    def __init__(self) -> None:
        self._cache = CacheManager()

    async def fetch(
        self,
        lng: float,
        lat: float,
        buffer_m: float = 1000,
        **kwargs: Any,
    ) -> ConnectorResult:
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            return await self._fallback_to_cache()

        mgt_no = kwargs.get("mgt_no", "")

        # 1차: MaritimeService (mgtNo 필수)
        if mgt_no:
            try:
                async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                    resp = await client.get(
                        "https://apis.data.go.kr/1480523/MaritimeService/getIvstg",
                        params={
                            "serviceKey": api_key,
                            "pageNo": 1,
                            "numOfRows": 10,
                            "type": "json",
                            "mgtNo": mgt_no,
                        },
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        rc = data.get("response", {}).get("header", {}).get("resultCode", "")
                        if rc == "00":
                            self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
                            return self._make_result(data)
            except Exception as e:
                logger.info("MaritimeService failed: %s", e)

        # 2차: 해양수산부 EnvImpactService (목록 조회)
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                resp = await client.get(
                    "https://apis.data.go.kr/1192000/service/EnvImpactService/getEnvImpactInfo",
                    params={
                        "ServiceKey": api_key,
                        "pageNo": 1,
                        "numOfRows": 5,
                        "resultType": "json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    info = data.get("getEnvImpactInfo", {})
                    if info.get("header", {}).get("code") == "00":
                        self._cache.save_snapshot(self.name, f"{lat}_{lng}", data)
                        return self._make_result(data)
        except Exception as e:
            logger.info("MOF EnvImpact API failed: %s", e)

        return await self._fallback_to_cache("Marine APIs unavailable")

    async def _fallback_to_cache(self, error: str = "") -> ConnectorResult:
        data, freshness = self._cache.load_snapshot(self.name)
        if data:
            return self._make_result(data, ConnectorStatus.UNSTABLE, freshness)
        return self._make_error(error or "No API key and no cache available")

