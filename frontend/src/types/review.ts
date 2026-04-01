/** 검토의견 예측 + 품질 체크 타입 정의. */

// ── 검토의견 예측 ──

export interface PredictedComment {
  category: string;
  comment: string;
  probability_pct: number;
  past_count: number;
  total_past_cases: number;
  risk_matched: boolean;
  severity: "high" | "medium" | "low";
}

export interface ReviewPredictionResponse {
  project_type: string;
  korean_type: string;
  total_past_cases: number;
  predicted_comments: PredictedComment[];
  avg_review_months: number | null;
  supplement_required_pct: number | null;
  disclaimer: string;
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface ReviewPredictionRequest {}

// ── 품질 체크 ──

export interface QualityCheckItem {
  check_id: string;
  category: string;
  title: string;
  status: "pass" | "warning" | "fail";
  detail: string;
}

export interface QualityCheckResponse {
  overall_status: "pass" | "warning" | "fail";
  score: number;
  total_checks: number;
  passed: number;
  warnings: number;
  failed: number;
  checks: QualityCheckItem[];
  summary: Record<string, string>;
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface QualityCheckRequest {}
