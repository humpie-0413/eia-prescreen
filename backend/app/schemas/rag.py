"""RAG(Retrieval-Augmented Generation) Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """RAG 질의 요청."""

    question: str = Field(..., min_length=2, description="질문 텍스트")
    n_results: int = Field(default=5, ge=1, le=20, description="검색할 유사 청크 수")
    project_type: str | None = Field(default=None, description="사업유형 필터 (도로/발전소/산업단지/주거/관광)")


class RAGSourceInfo(BaseModel):
    """RAG 검색 출처 정보."""

    report_id: str = ""
    project_name: str = ""
    project_type: str = ""
    year: str = ""
    chapter: str = ""
    section: str = ""
    page_range: str = ""
    similarity: float = 0.0
    excerpt: str = ""


class RAGQueryResponse(BaseModel):
    """RAG 질의 응답."""

    answer: str
    sources: list[RAGSourceInfo] = Field(default_factory=list)
    total_indexed: int = 0
    generated_at: str | None = None
    disclaimer: str = "이 답변은 실제 환경영향평가서 원문을 참조한 AI 생성 결과이며, 참고용입니다."


class DraftAssistRequest(BaseModel):
    """Draft Copilot RAG 보조 요청."""

    section_topic: str = Field(..., description="섹션 주제 (예: 대기질, 수질)")
    project_type: str = Field(..., description="사업유형 코드 (예: road, housing)")
    risk_cards: list[dict] = Field(default_factory=list, description="리스크 카드 목록")


class DraftAssistResponse(BaseModel):
    """Draft Copilot RAG 보조 응답."""

    available: bool = False
    reference_text: str = ""
    sources: list[dict] = Field(default_factory=list)
    section_topic: str = ""
    project_type: str = ""


class RAGStatsResponse(BaseModel):
    """RAG 색인 통계 응답."""

    status: str = "not_initialized"
    total_chunks: int = 0
    total_reports: int = 0
    by_project_type: dict[str, int] = Field(default_factory=dict)
    embed_model: str = ""
    chroma_dir: str = ""


class RAGIndexRequest(BaseModel):
    """RAG 색인 요청."""

    overwrite: bool = Field(default=False, description="기존 색인 덮어쓰기")


class RAGIndexResponse(BaseModel):
    """RAG 색인 응답."""

    total_files: int = 0
    total_chunks: int = 0
    reports: list[dict] = Field(default_factory=list)
    error: str | None = None
