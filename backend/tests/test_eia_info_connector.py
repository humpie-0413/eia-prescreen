"""EiaInfoConnector 테스트."""

import pytest
from backend.app.connectors.eia_info import (
    EiaInfoConnector,
    _haversine_km,
    _parse_xml_items,
    GUBUN_LABELS,
)


class TestHaversine:
    """거리 계산 테스트."""

    def test_same_point(self) -> None:
        assert _haversine_km(37.5, 127.0, 37.5, 127.0) == 0.0

    def test_seoul_to_busan(self) -> None:
        # Seoul to Busan ~325km
        dist = _haversine_km(37.5665, 126.9780, 35.1796, 129.0756)
        assert 320 < dist < 340

    def test_short_distance(self) -> None:
        # ~1km
        dist = _haversine_km(37.5, 127.0, 37.509, 127.0)
        assert 0.8 < dist < 1.2


class TestParseXml:
    """XML 파싱 테스트."""

    def test_parse_items(self) -> None:
        xml = """<?xml version="1.0"?>
        <response><body><items>
            <item><name>테스트사업</name><centerx>127.0</centerx><centery>37.5</centery><distance>100</distance><num>1</num></item>
            <item><name>두번째</name><centerx>128.0</centerx><centery>36.0</centery><distance>200</distance><num>2</num></item>
        </items></body></response>"""
        items = _parse_xml_items(xml)
        assert len(items) == 2
        assert items[0]["name"] == "테스트사업"
        assert items[0]["centerx"] == "127.0"
        assert items[1]["num"] == "2"

    def test_empty_response(self) -> None:
        xml = """<?xml version="1.0"?><response><body><items></items></body></response>"""
        assert _parse_xml_items(xml) == []

    def test_malformed_xml_regex_fallback(self) -> None:
        # Not valid XML but has item tags
        text = "<item><name>사업A</name><num>1</num></item><item><name>사업B</name></item>"
        items = _parse_xml_items(text)
        assert len(items) == 2


class TestGubunLabels:
    """gubun 라벨 테스트."""

    def test_all_15_defined(self) -> None:
        assert len(GUBUN_LABELS) == 15
        for i in range(1, 16):
            assert i in GUBUN_LABELS


class TestFilterByDistance:
    """거리 필터링 테스트."""

    def test_filter_nearby(self) -> None:
        connector = EiaInfoConnector()
        items = [
            {"name": "가까운", "centerx": "127.001", "centery": "37.501"},
            {"name": "먼곳", "centerx": "130.0", "centery": "35.0"},
        ]
        filtered = connector._filter_by_distance(items, 37.5, 127.0, radius_km=5.0)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "가까운"
        assert "_dist_km" in filtered[0]

    def test_sorted_by_distance(self) -> None:
        connector = EiaInfoConnector()
        items = [
            {"name": "중간", "centerx": "127.02", "centery": "37.52"},
            {"name": "가까운", "centerx": "127.001", "centery": "37.501"},
        ]
        filtered = connector._filter_by_distance(items, 37.5, 127.0, radius_km=10.0)
        assert len(filtered) == 2
        assert filtered[0]["name"] == "가까운"

    def test_invalid_coords_skipped(self) -> None:
        connector = EiaInfoConnector()
        items = [
            {"name": "유효", "centerx": "127.0", "centery": "37.5"},
            {"name": "무효", "centerx": "invalid", "centery": "abc"},
            {"name": "영점", "centerx": "0", "centery": "0"},
        ]
        filtered = connector._filter_by_distance(items, 37.5, 127.0, radius_km=100.0)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "유효"


