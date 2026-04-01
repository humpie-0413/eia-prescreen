import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from backend.app.connectors.base import DataFreshness
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """파일 기반 스냅샷 캐시 매니저.

    스냅샷 저장 경로: data/snapshots/{connector}_{region}_{timestamp}.json
    """

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self._cache_dir = Path(cache_dir or settings.CACHE_DIR)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_hours = settings.CACHE_TTL_HOURS

    def save_snapshot(
        self,
        connector_name: str,
        region: str,
        data: Any,
        metadata: Optional[dict] = None,
    ) -> Path:
        """스냅샷을 JSON 파일로 저장한다."""
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        filename = f"{connector_name}_{region}_{ts}.json"
        filepath = self._cache_dir / filename

        snapshot = {
            "connector_name": connector_name,
            "region": region,
            "snapshot_at": now.isoformat(),
            "metadata": metadata or {},
            "data": data,
        }

        filepath.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Snapshot saved: %s", filepath.name)
        return filepath

    def load_snapshot(
        self,
        connector_name: str,
        region: str = "",
    ) -> tuple[Optional[Any], DataFreshness]:
        """가장 최근 스냅샷을 로드한다.

        Returns:
            (data, DataFreshness) — 스냅샷이 없으면 (None, stale freshness)
        """
        pattern = f"{connector_name}_{region}_*.json" if region else f"{connector_name}_*.json"
        files = sorted(self._cache_dir.glob(pattern), reverse=True)

        if not files:
            return None, DataFreshness(freshness="unknown")

        latest = files[0]
        try:
            raw = json.loads(latest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to read snapshot: %s", latest.name)
            return None, DataFreshness(freshness="unknown")

        snapshot_at = datetime.fromisoformat(raw["snapshot_at"])
        age = datetime.now() - snapshot_at
        is_stale = age > timedelta(hours=self._ttl_hours)

        freshness = DataFreshness(
            snapshot_at=snapshot_at,
            fallback_used=True,
            freshness="stale" if is_stale else "cached",
        )

        return raw.get("data"), freshness

    def list_snapshots(self, connector_name: Optional[str] = None) -> list[dict]:
        """저장된 스냅샷 목록을 반환한다."""
        pattern = f"{connector_name}_*.json" if connector_name else "*.json"
        results = []
        for f in sorted(self._cache_dir.glob(pattern), reverse=True):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                results.append({
                    "filename": f.name,
                    "connector_name": raw.get("connector_name"),
                    "region": raw.get("region"),
                    "snapshot_at": raw.get("snapshot_at"),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results
