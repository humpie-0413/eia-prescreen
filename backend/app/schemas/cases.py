from pydantic import BaseModel, Field


class CaseResponse(BaseModel):
    case_id: str
    project_name: str | None = None
    year: str | None = None
    project_type: str
    location_type: str
    region: str
    key_issues: list[str] = []
    remediation_required: list[str] = []
    public_concerns: list[str] = []
    consultation_result: str
    source_document: str
    summary: str
    tags: list[str] = []
    lessons_learned: str | None = None
    similarity_score: float | None = None


class CaseSearchQuery(BaseModel):
    project_type: str | None = None
    location_type: str | None = None
    keyword: str | None = None
    tags: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=50)


class CaseSearchResponse(BaseModel):
    cases: list[CaseResponse]
    total: int


class InterpretationResponse(BaseModel):
    interpretation: str
    model: str
    generated_at: str
    disclaimer: str
    ai_generated: str


class ReportRequest(BaseModel):
    report_type: str = Field(
        ...,
        pattern="^(brief|full|checklist)$",
        description="Report type: brief (1p), full (5-10p), or checklist"
    )
    scenario: str = Field(default="yangpyeong")
