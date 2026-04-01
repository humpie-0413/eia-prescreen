"""Tests for CacheManager and connector fallback behaviour.

Uses ``tmp_path`` for full isolation — every test gets its own snapshot
directory so nothing leaks between runs.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio  # noqa: F401  (ensures the plugin is importable)

from backend.app.connectors.base import ConnectorStatus, DataFreshness
from backend.app.services.cache_manager import CacheManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_DATA = {"zone_type": "test-zone", "score": 42}
SAMPLE_META = {"source": "unit-test"}


def _make_cache(tmp_path: Path) -> CacheManager:
    """Build a CacheManager whose cache_dir points at *tmp_path*."""
    return CacheManager(cache_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# 1. save_snapshot creates a file with correct JSON
# ---------------------------------------------------------------------------


def test_save_snapshot_creates_file(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)
    filepath = cache.save_snapshot("land_use", "seoul", SAMPLE_DATA, SAMPLE_META)

    # File must exist inside the tmp cache dir
    assert filepath.exists()
    assert filepath.parent == tmp_path

    # Filename pattern: {connector}_{region}_{timestamp}.json
    assert filepath.name.startswith("land_use_seoul_")
    assert filepath.suffix == ".json"

    # Contents must be valid JSON with the right fields
    raw = json.loads(filepath.read_text(encoding="utf-8"))
    assert raw["connector_name"] == "land_use"
    assert raw["region"] == "seoul"
    assert raw["data"] == SAMPLE_DATA
    assert raw["metadata"] == SAMPLE_META
    # snapshot_at must be a valid ISO timestamp
    datetime.fromisoformat(raw["snapshot_at"])


# ---------------------------------------------------------------------------
# 2. load_snapshot returns data + freshness with fallback_used=True
# ---------------------------------------------------------------------------


def test_load_snapshot_returns_data_and_freshness(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)
    cache.save_snapshot("land_use", "seoul", SAMPLE_DATA)

    data, freshness = cache.load_snapshot("land_use", "seoul")

    assert data == SAMPLE_DATA
    assert isinstance(freshness, DataFreshness)
    assert freshness.freshness == "cached"
    assert freshness.fallback_used is True
    assert freshness.snapshot_at is not None


# ---------------------------------------------------------------------------
# 3. load_snapshot from empty dir → (None, freshness="unknown")
# ---------------------------------------------------------------------------


def test_load_snapshot_no_cache_returns_none(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)

    data, freshness = cache.load_snapshot("land_use", "seoul")

    assert data is None
    assert freshness.freshness == "unknown"


# ---------------------------------------------------------------------------
# 4. list_snapshots returns both in reverse chronological order
# ---------------------------------------------------------------------------


def test_list_snapshots(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)

    # Use the same region so filename ordering is determined solely by timestamp
    cache.save_snapshot("land_use", "seoul", {"v": 1})
    time.sleep(1.1)  # ensure distinct second-level timestamp
    cache.save_snapshot("land_use", "seoul", {"v": 2})

    result = cache.list_snapshots("land_use")

    assert len(result) == 2

    # list_snapshots sorts filenames in reverse order (newest timestamp first)
    snap_times = [datetime.fromisoformat(r["snapshot_at"]) for r in result]
    assert snap_times[0] > snap_times[1], "Expected reverse chronological order"

    # The newest snapshot should carry the second payload's timestamp
    raw_newest = json.loads(
        (tmp_path / result[0]["filename"]).read_text(encoding="utf-8")
    )
    assert raw_newest["data"] == {"v": 2}

    # Each entry has the expected keys
    for entry in result:
        assert "filename" in entry
        assert "connector_name" in entry
        assert "region" in entry
        assert "snapshot_at" in entry


# ---------------------------------------------------------------------------
# 5. Stale detection — snapshot_at pushed beyond TTL
# ---------------------------------------------------------------------------


def test_stale_detection(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)
    filepath = cache.save_snapshot("land_use", "seoul", SAMPLE_DATA)

    # Manually rewrite snapshot_at to 25 hours ago (beyond default 24-h TTL)
    raw = json.loads(filepath.read_text(encoding="utf-8"))
    past = datetime.now() - timedelta(hours=25)
    raw["snapshot_at"] = past.isoformat()
    filepath.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    data, freshness = cache.load_snapshot("land_use", "seoul")

    assert data == SAMPLE_DATA
    assert freshness.freshness == "stale"
    assert freshness.fallback_used is True


# ---------------------------------------------------------------------------
# 6. Connector fallback when API key is missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connector_fallback_on_failure(tmp_path: Path) -> None:
    """LandUseConnector.fetch() falls back to cache when API key is empty.

    We patch CacheManager.__init__ so the connector's internal cache points
    at our tmp_path, then patch settings.DATA_GO_KR_API_KEY to be empty.
    """
    from backend.app.connectors.land_use import LandUseConnector

    # Pre-populate the cache directory with a known snapshot
    cache = _make_cache(tmp_path)
    cache.save_snapshot("land_use", "", SAMPLE_DATA, SAMPLE_META)

    # Patch CacheManager so the connector reuses our tmp-based cache
    original_init = CacheManager.__init__

    def _patched_init(self, cache_dir=None):  # noqa: ANN001
        original_init(self, cache_dir=str(tmp_path))

    with (
        patch.object(CacheManager, "__init__", _patched_init),
        patch("backend.app.connectors.land_use.settings") as mock_settings,
    ):
        mock_settings.DATA_GO_KR_API_KEY = ""

        connector = LandUseConnector()
        result = await connector.fetch(lng=127.0, lat=37.5)

    # The connector should return cached data with STABLE status
    assert result.status == ConnectorStatus.STABLE
    assert result.data == SAMPLE_DATA
    assert result.freshness.fallback_used is True
    assert result.freshness.freshness in ("cached", "stale")
