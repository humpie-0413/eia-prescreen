"""RAG(Retrieval-Augmented Generation) API 라우터.

환경영향평가서 원문 기반 질의응답 + Draft Copilot 보조 엔드포인트.
"""

import logging

from fastapi import APIRouter, HTTPException

from backend.app.schemas.rag import (
    DraftAssistRequest,
    DraftAssistResponse,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGStatsResponse,
)
from backend.app.services.report_rag import ReportRAG

logger = logging.getLogger(__name__)

router = APIRouter()

# RAG 서비스 싱글턴 (lazy init)
_rag: ReportRAG | None = None


def _get_rag() -> ReportRAG:
    """RAG 서비스 인스턴스를 반환한다 (lazy 초기화)."""
    global _rag
    if _rag is None:
        _rag = ReportRAG()
        try:
            _rag.load()
        except Exception as exc:
            logger.warning("RAG 서비스 초기화 실패 (색인 없을 수 있음): %s", exc)
    return _rag


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """RAG 질의: 실제 평가서 원문을 검색하여 근거 기반 답변을 생성한다.

    예: "도로 사업의 비산먼지 저감방안은?"
    """
    rag = _get_rag()
    result = await rag.query(
        question=request.question,
        n_results=request.n_results,
        project_type=request.project_type,
    )
    return RAGQueryResponse(**result)


@router.post("/draft-assist", response_model=DraftAssistResponse)
async def rag_draft_assist(request: DraftAssistRequest) -> DraftAssistResponse:
    """Draft Copilot 보조: 초안 생성 시 실제 평가서 문장을 참조한다."""
    rag = _get_rag()
    result = await rag.draft_assist(
        section_topic=request.section_topic,
        project_type=request.project_type,
        risk_cards=request.risk_cards,
    )
    return DraftAssistResponse(**result)


@router.get("/stats", response_model=RAGStatsResponse)
async def rag_stats() -> RAGStatsResponse:
    """색인 통계: 색인된 보고서 수, 청크 수, 사업유형별 분포."""
    rag = _get_rag()
    stats = rag.get_stats()
    return RAGStatsResponse(**stats)


@router.post("/index", response_model=RAGIndexResponse)
async def rag_index(request: RAGIndexRequest) -> RAGIndexResponse:
    """색인 실행: 추출된 보고서 텍스트를 ChromaDB에 색인한다."""
    rag = _get_rag()
    try:
        result = rag.index_reports(overwrite=request.overwrite)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return RAGIndexResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("색인 실행 오류: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
