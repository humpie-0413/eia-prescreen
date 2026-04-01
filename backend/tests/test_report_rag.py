"""RAG 서비스 테스트.

ChromaDB + 임베딩 의존성 없이 핵심 로직을 테스트한다.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))


# ── 텍스트 추출 테스트 ──

class TestExtractReportText:
    """extract_report_text.py 핵심 로직 테스트."""

    def test_infer_metadata_from_filename(self):
        from backend.scripts.extract_report_text import _infer_metadata_from_filename

        meta = _infer_metadata_from_filename("road_양평국도건설_2023.pdf")
        assert meta["project_type_code"] == "road"
        assert meta["project_type"] == "도로건설"
        assert meta["project_name"] == "양평국도건설"
        assert meta["year"] == "2023"

    def test_infer_metadata_power_plant(self):
        from backend.scripts.extract_report_text import _infer_metadata_from_filename

        meta = _infer_metadata_from_filename("power_plant_보령화력_2022.pdf")
        assert meta["project_type_code"] == "power_plant"
        assert meta["project_type"] == "에너지개발"

    def test_infer_metadata_new_types(self):
        from backend.scripts.extract_report_text import _infer_metadata_from_filename

        meta = _infer_metadata_from_filename("urban_dev_세종시택지_2024.pdf")
        assert meta["project_type_code"] == "urban_dev"
        assert meta["project_type"] == "도시개발"

        meta = _infer_metadata_from_filename("railway_GTX_2025.pdf")
        assert meta["project_type_code"] == "railway"
        assert meta["project_type"] == "철도건설"

        meta = _infer_metadata_from_filename("waste_소각시설_2023.pdf")
        assert meta["project_type_code"] == "waste"
        assert meta["project_type"] == "폐기물처리시설"

    def test_infer_metadata_unknown(self):
        from backend.scripts.extract_report_text import _infer_metadata_from_filename

        meta = _infer_metadata_from_filename("some_file.pdf")
        assert meta["project_type_code"] == "some"

    def test_detect_chapters_empty(self):
        from backend.scripts.extract_report_text import _detect_chapters

        result = _detect_chapters([])
        assert result == []

    def test_detect_chapters_with_chapter_pattern(self):
        from backend.scripts.extract_report_text import _detect_chapters

        pages = [
            {
                "page": 1,
                "text": "제1장 사업의 개요\n본 사업은 도로건설 사업이다.\n사업의 목적은 교통 개선이다.",
            },
            {
                "page": 2,
                "text": "제2장 지역 개황\n사업지 주변의 자연환경 현황을 기술한다.",
            },
        ]
        result = _detect_chapters(pages)
        assert len(result) >= 2
        assert result[0]["chapter"] == "제1장"
        assert "도로건설" in result[0]["content"]

    def test_detect_chapters_with_section_pattern(self):
        from backend.scripts.extract_report_text import _detect_chapters

        pages = [
            {
                "page": 1,
                "text": "제1장 사업의 개요\n내용...\n1.1 사업의 목적\n목적 내용\n1.2 사업의 내용\n내용 설명",
            },
        ]
        result = _detect_chapters(pages)
        assert len(result) >= 2

    def test_detect_chapters_no_pattern(self):
        from backend.scripts.extract_report_text import _detect_chapters

        pages = [{"page": 1, "text": "일반 텍스트 내용만 있음"}]
        result = _detect_chapters(pages)
        assert len(result) == 1
        assert result[0]["chapter"] == "전체"


# ── 청킹 테스트 ──

class TestChunking:
    """텍스트 청킹 로직 테스트."""

    def test_chunk_empty(self):
        from backend.app.services.report_rag import _chunk_text

        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    def test_chunk_short_text(self):
        from backend.app.services.report_rag import _chunk_text

        text = "짧은 텍스트입니다."
        chunks = _chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert "짧은 텍스트" in chunks[0]

    def test_chunk_long_text(self):
        from backend.app.services.report_rag import _chunk_text

        text = "\n\n".join([f"문단 {i}. " + "가나다라" * 50 for i in range(10)])
        chunks = _chunk_text(text, chunk_size=200, overlap=0)
        assert len(chunks) > 1

    def test_chunk_overlap(self):
        from backend.app.services.report_rag import _chunk_text

        text = "첫번째 문단입니다.\n\n두번째 문단입니다.\n\n세번째 문단입니다."
        chunks = _chunk_text(text, chunk_size=20, overlap=5)
        if len(chunks) > 1:
            # overlap이 적용되면 두 번째 청크가 이전 청크 끝부분을 포함
            assert len(chunks[1]) > len("두번째 문단입니다.")


# ── RAG 서비스 테스트 ──

class TestReportRAG:
    """ReportRAG 서비스 테스트 (의존성 모킹)."""

    def test_get_stats_not_loaded(self):
        """로드되지 않은 상태에서 stats 호출."""
        from backend.app.services.report_rag import ReportRAG

        with patch("backend.app.services.report_rag.ReportRAG.load"):
            rag = ReportRAG()
            stats = rag.get_stats()
            assert stats["status"] == "not_initialized"
            assert stats["total_chunks"] == 0

    @pytest.mark.asyncio
    async def test_query_no_index(self):
        """색인이 없는 상태에서 query 호출."""
        from backend.app.services.report_rag import ReportRAG

        rag = ReportRAG()
        rag._loaded = True
        rag._collection = MagicMock()
        rag._collection.count.return_value = 0

        result = await rag.query("테스트 질문")
        assert "색인된 평가서가 없" in result["answer"]
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_draft_assist_no_index(self):
        """색인이 없는 상태에서 draft_assist 호출."""
        from backend.app.services.report_rag import ReportRAG

        rag = ReportRAG()
        rag._loaded = True
        rag._collection = MagicMock()
        rag._collection.count.return_value = 0

        result = await rag.draft_assist("대기질", "road")
        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_query_with_results(self):
        """검색 결과가 있을 때 LLM 답변 생성."""
        from backend.app.services.report_rag import ReportRAG

        rag = ReportRAG()
        rag._loaded = True
        rag._embed_model = MagicMock()

        # search를 모킹
        mock_chunks = [
            {
                "id": "test_chunk_1",
                "content": "비산먼지 저감을 위해 살수차를 운영한다.",
                "metadata": {
                    "report_id": "road_양평_2023",
                    "project_name": "양평국도건설",
                    "project_type": "도로",
                    "year": "2023",
                    "chapter": "제4장",
                    "section": "4.1 저감방안",
                    "page_range": "45-47",
                },
                "distance": 0.2,
                "similarity": 0.8,
            },
        ]

        with patch.object(rag, "search", return_value=mock_chunks), \
             patch.object(rag, "_generate_answer", new_callable=AsyncMock, return_value="테스트 답변"):
            rag._collection = MagicMock()
            rag._collection.count.return_value = 100
            result = await rag.query("비산먼지 저감방안")
            assert result["answer"] == "테스트 답변"
            assert len(result["sources"]) == 1
            assert result["sources"][0]["project_name"] == "양평국도건설"


# ── 크롤러 유틸 테스트 ──

class TestCrawlerUtils:
    """crawl_eiass_reports.py 유틸리티 함수 테스트."""

    def test_safe_filename(self):
        from backend.scripts.crawl_eiass_reports import _safe_filename

        assert _safe_filename("양평 도로 건설 사업") == "양평_도로_건설_사업"
        assert _safe_filename('file:name*test?"yes"') == "filenametestyes"
        assert len(_safe_filename("a" * 100)) == 80

    def test_load_manifest_empty(self, tmp_path):
        from backend.scripts.crawl_eiass_reports import _load_manifest

        with patch("backend.scripts.crawl_eiass_reports.MANIFEST_PATH", tmp_path / "missing.json"):
            manifest = _load_manifest()
            assert manifest["downloaded"] == []
            assert manifest["failed"] == []

    def test_save_and_load_manifest(self, tmp_path):
        from backend.scripts.crawl_eiass_reports import _load_manifest, _save_manifest

        manifest_path = tmp_path / "test_manifest.json"
        with patch("backend.scripts.crawl_eiass_reports.MANIFEST_PATH", manifest_path):
            manifest = {"downloaded": [{"title": "test"}], "failed": [], "last_run": None}
            _save_manifest(manifest)
            assert manifest_path.exists()

            loaded = _load_manifest()
            assert len(loaded["downloaded"]) == 1
            assert loaded["downloaded"][0]["title"] == "test"


# ── RAG API 스키마 테스트 ──

class TestRAGSchemas:
    """RAG Pydantic 스키마 유효성 테스트."""

    def test_rag_query_request_valid(self):
        from backend.app.schemas.rag import RAGQueryRequest

        req = RAGQueryRequest(question="도로 사업 비산먼지 저감방안은?")
        assert req.question == "도로 사업 비산먼지 저감방안은?"
        assert req.n_results == 5
        assert req.project_type is None

    def test_rag_query_request_with_filter(self):
        from backend.app.schemas.rag import RAGQueryRequest

        req = RAGQueryRequest(question="수질 현황", project_type="도로", n_results=3)
        assert req.project_type == "도로"
        assert req.n_results == 3

    def test_rag_query_request_too_short(self):
        from backend.app.schemas.rag import RAGQueryRequest

        with pytest.raises(Exception):
            RAGQueryRequest(question="")

    def test_draft_assist_request(self):
        from backend.app.schemas.rag import DraftAssistRequest

        req = DraftAssistRequest(section_topic="대기질", project_type="road")
        assert req.section_topic == "대기질"
        assert req.risk_cards == []

    def test_rag_stats_response(self):
        from backend.app.schemas.rag import RAGStatsResponse

        resp = RAGStatsResponse(
            status="ready",
            total_chunks=500,
            total_reports=10,
            by_project_type={"도로": 200, "발전소": 300},
        )
        assert resp.total_chunks == 500
        assert resp.by_project_type["도로"] == 200
