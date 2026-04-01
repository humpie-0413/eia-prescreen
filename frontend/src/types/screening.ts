export type ProjectType =
  | "urban_dev" | "industrial" | "energy" | "port"
  | "road" | "water_resource" | "railway" | "airport"
  | "river" | "tourism" | "mountain" | "sports"
  | "waste" | "military" | "mining" | "reclamation"
  | "special_area" | "etc"
  // 이전 호환
  | "housing" | "power_plant" | "factory" | "other";

export type Severity = "critical" | "major" | "review" | "info";

export type Freshness = "live" | "cached" | "stale" | "demo" | "unknown";

export interface LocationInput {
  lng: number;
  lat: number;
}

export interface ScreeningInput {
  project_name: string;
  project_type: ProjectType;
  project_scale?: string;
  address?: string;
  location?: LocationInput;
  boundary_geojson?: Record<string, unknown>;
}

export interface RiskCard {
  id: string;
  rule_id: string;
  rule_version: string;
  title: string;
  severity: Severity;
  rationale: string;
  evidence: Record<string, unknown> | null;
  next_action: string | null;
  legal_basis: string | null;
  confidence: number | null;
  human_review_required: boolean;
  trigger_dataset: string | null;
  source_snapshot_date: string | null;
}

export interface RegulationMatch {
  id: string;
  regulation_name: string;
  regulation_code: string | null;
  legal_basis: string;
  description: string | null;
  restriction_level: string | null;
  permit_required: boolean;
  related_authority: string | null;
  evidence: Record<string, unknown> | null;
}

export interface ScreeningResponse {
  id: string;
  project_name: string;
  project_type: ProjectType;
  project_scale: string | null;
  address: string | null;
  lng?: number;
  lat?: number;
  status: string;
  llm_interpretation: string | null;
  created_at: string;
  updated_at: string;
  risk_cards: RiskCard[];
  regulation_matches: RegulationMatch[];
}

export interface ScreeningSummary {
  id: string;
  project_name: string;
  project_type: ProjectType;
  status: string;
  created_at: string;
  risk_card_count: number;
  critical_count: number;
  major_count: number;
}

export interface DataFreshnessInfo {
  fetched_at: string | null;
  snapshot_at: string | null;
  fallback_used: boolean;
  freshness: Freshness;
}

export interface ConnectorStatus {
  name: string;
  tier: "A" | "B" | "C";
  description: string;
  status: "stable" | "unstable" | "unavailable" | "unknown";
  freshness: DataFreshnessInfo | null;
  has_data: boolean;
  error: string | null;
}

export interface DataStatusResponse {
  demo_mode: boolean;
  connectors: ConnectorStatus[];
  total: number;
  available: number;
}

export interface ScreeningDataStatusResponse {
  screening_id: string | null;
  demo_mode: boolean;
  connectors: ConnectorStatus[];
  total: number;
  available: number;
  coverage_pct: number;
  freshness_summary: Record<string, number>;
}

export interface ConnectorListResponse {
  connectors: ConnectorStatus[];
  total: number;
}

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  urban_dev: "도시개발",
  industrial: "산업입지",
  energy: "에너지개발",
  port: "항만건설",
  road: "도로건설",
  water_resource: "수자원개발",
  railway: "철도건설",
  airport: "공항건설",
  river: "하천이용개발",
  tourism: "관광단지개발",
  mountain: "산지개발",
  sports: "체육시설",
  waste: "폐기물처리시설",
  military: "국방군사시설",
  mining: "토석광물채취",
  reclamation: "매립간척",
  special_area: "특정지역",
  etc: "기타",
  // 이전 호환
  housing: "주거",
  power_plant: "발전소",
  factory: "공장",
  other: "기타",
};

export interface EvaluationSummary {
  total_risks: number;
  critical_count: number;
  major_count: number;
  review_count: number;
  info_count: number;
  total_regulations: number;
  permit_required_count: number;
}

export interface EvaluationResponse {
  screening_id: string;
  status: string;
  risk_cards: RiskCard[];
  regulation_matches: RegulationMatch[];
  summary: EvaluationSummary;
}

export interface ChecklistItem {
  id: number;
  category: string;
  title: string;
  description: string;
  legal_basis: string | null;
  priority: string;
  checked: boolean;
  related_rule_id: string | null;
}

export interface ChecklistSection {
  section_name: string;
  priority: string;
  items: ChecklistItem[];
}

export interface ChecklistResponse {
  screening_id: string | null;
  total_items: number;
  sections: ChecklistSection[];
  generated_at: string;
}

// ── Cases ──

export interface CaseResult {
  case_id: string;
  project_name: string | null;
  year: string | null;
  project_type: string;
  location_type: string;
  region: string;
  key_issues: string[];
  remediation_required: string[];
  public_concerns: string[];
  consultation_result: string;
  source_document: string;
  summary: string;
  tags: string[];
  lessons_learned: string | null;
  similarity_score: number | null;
}

export interface CaseSearchResponse {
  cases: CaseResult[];
  total: number;
}

export interface InterpretationResponse {
  interpretation: string;
  model: string;
  generated_at: string;
  disclaimer: string;
  ai_generated: string;
}

// ── Compare ──

export interface SiteRiskSummary {
  screening_id: string;
  project_name: string;
  project_type: string;
  address: string | null;
  total_risks: number;
  critical_count: number;
  major_count: number;
  review_count: number;
  info_count: number;
  total_regulations: number;
  permit_required_count: number;
  risk_cards: Record<string, unknown>[];
  regulation_matches: Record<string, unknown>[];
}

export interface RiskComparisonRow {
  rule_id: string;
  title: string;
  severity_by_site: Record<string, string | null>;
}

export interface CompareResponse {
  sites: SiteRiskSummary[];
  risk_matrix: RiskComparisonRow[];
  recommendation: string;
}

export const SEVERITY_CONFIG: Record<
  Severity,
  { label: string; color: string; bg: string }
> = {
  critical: { label: "Critical", color: "text-red-700 dark:text-red-400", bg: "bg-red-100 dark:bg-red-950" },
  major: { label: "Major", color: "text-orange-700 dark:text-orange-400", bg: "bg-orange-100 dark:bg-orange-950" },
  review: { label: "Review", color: "text-yellow-700 dark:text-yellow-400", bg: "bg-yellow-100 dark:bg-yellow-950" },
  info: { label: "Info", color: "text-blue-700 dark:text-blue-400", bg: "bg-blue-100 dark:bg-blue-950" },
};
