/** Draft Copilot 타입 정의. */

export interface DraftSection {
  section_id: string;
  chapter: string;
  title: string;
  content: string;
  auto_generated: boolean;
  field_survey_required: boolean;
  badge: "자동 생성" | "현장조사 필요" | "전문가 검토 필요";
  generated_at: string | null;
  disclaimer: string;
  llm_generated?: boolean;
}

export interface DraftFullResponse {
  project_info: Record<string, string>;
  sections: DraftSection[];
  total_sections: number;
  generated_at: string | null;
  disclaimer: string;
}

export interface DraftRequest {
  project_name?: string;
  project_type?: string;
  project_scale?: string;
  address?: string;
  use_llm?: boolean;
}

export interface TemplateSectionInfo {
  section_id: string;
  title: string;
  auto_generable: boolean;
  field_survey_required: boolean;
  data_sources: string[];
  description: string;
}

export interface TemplateChapter {
  chapter_id: string;
  title: string;
  sections: TemplateSectionInfo[];
}

export interface TemplateResponse {
  title: string;
  version: string;
  chapters: TemplateChapter[];
  metadata: Record<string, unknown>;
}
