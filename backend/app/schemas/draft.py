"""Draft Copilot Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftSectionResponse(BaseModel):
    """단일 섹션 초안 응답."""

    section_id: str
    chapter: str
    title: str
    content: str
    auto_generated: bool = True
    field_survey_required: bool = False
    badge: str = "자동 생성"
    generated_at: str | None = None
    disclaimer: str = "이 초안은 AI가 생성한 참고 자료이며 전문가 검토가 필요합니다"
    llm_generated: bool = False


class DraftFullResponse(BaseModel):
    """전체 초안 응답."""

    project_info: dict = Field(default_factory=dict)
    sections: list[DraftSectionResponse] = Field(default_factory=list)
    total_sections: int = 0
    generated_at: str | None = None
    disclaimer: str = "이 초안은 AI가 생성한 참고 자료이며 전문가 검토가 필요합니다"


class DraftRequest(BaseModel):
    """초안 생성 요청."""

    project_name: str | None = None
    project_type: str | None = None
    project_scale: str | None = None
    address: str | None = None
    use_llm: bool = False


class TemplateSectionInfo(BaseModel):
    """템플릿 섹션 정보."""

    section_id: str
    title: str
    auto_generable: bool = True
    field_survey_required: bool = False
    data_sources: list[str] = Field(default_factory=list)
    description: str = ""


class TemplateChapterInfo(BaseModel):
    """템플릿 챕터 정보."""

    chapter_id: str
    title: str
    sections: list[TemplateSectionInfo] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    """평가서 템플릿 구조 응답."""

    title: str = ""
    version: str = ""
    chapters: list[TemplateChapterInfo] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
