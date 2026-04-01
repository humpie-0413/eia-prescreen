// ── Pattern Analysis Types ──

export interface IssueItem {
  issue: string;
  count: number;
  pct: number;
}

export interface TypePatternDetail {
  korean_type: string;
  total_count: number;
  consultation_results: Record<string, number>;
  result_pct: Record<string, number>;
  common_issues: IssueItem[];
  avg_review_months: number | null;
  supplement_required_pct: number | null;
}

export interface PatternResponse {
  project_type: string;
  total_analyzed: number;
  overall_total: number;
  analysis_year_range: string;
  type_data: TypePatternDetail[];
}

export interface PredictedIssue {
  issue: string;
  probability_pct: number;
  past_count: number;
  total_in_type: number;
  description: string;
}

export interface RiskAssessment {
  location_type: string;
  risk_level: string;
  issue_probability: number;
  top_issues: string[];
  supplement_probability_pct: number;
}

export interface RemediationSuggestion {
  issue: string;
  common_remediation: string[];
  frequency: number;
}

export interface PredictionResponse {
  project_type: string;
  korean_type: string;
  total_in_type: number;
  predicted_issues: PredictedIssue[];
  consultation_prediction: Record<string, number>;
  avg_review_months: number | null;
  supplement_required_pct: number | null;
  risk_assessment: RiskAssessment | null;
  remediation_suggestions: RemediationSuggestion[];
}

export interface SuggestedRule {
  suggestion_id: string;
  title: string;
  source_type: string;
  issue: string;
  evidence: string;
  recommended_severity: string;
  rationale: string;
}

export interface SuggestedRulesResponse {
  suggestions: SuggestedRule[];
  total: number;
}

export interface OverallPatternSummary {
  total_count: number;
  year_range: string;
  analyzed_at: string;
  unique_biz_types: number;
  biz_type_distribution: Record<string, number>;
  step_distribution: Record<string, number>;
  available_types: string[];
}
