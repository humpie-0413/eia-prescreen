import type {
  CaseSearchResponse,
  ChecklistResponse,
  CompareResponse,
  ConnectorListResponse,
  DataStatusResponse,
  EvaluationResponse,
  InterpretationResponse,
  RegulationMatch,
  ScreeningDataStatusResponse,
  ScreeningInput,
  ScreeningResponse,
  ScreeningSummary,
} from "@/types/screening";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90_000);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...init?.headers },
      ...init,
      signal: init?.signal ?? controller.signal,
    });

    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      // 인증 비활성화 상태에서는 리다이렉트 하지 않음
      // window.location.href = "/login";
    }

    if (!res.ok) {
      const body = await res.text().catch(() => "Unknown error");
      throw new ApiError(res.status, body);
    }

    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      // 외부 signal로 취소된 경우 (탭 이동 등) — 조용히 중단
      if (init?.signal?.aborted) {
        throw err; // 원본 AbortError 전달 (컴포넌트에서 무시)
      }
      throw new ApiError(408, "요청 시간이 초과되었습니다 (90초)");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

/** 네트워크 오류 시 1회 자동 재시도 (AbortError·4xx 제외). */
async function requestWithRetry<T>(
  path: string,
  init?: RequestInit,
  retries = 1,
): Promise<T> {
  try {
    return await request<T>(path, init);
  } catch (err) {
    // AbortError — 재시도 안 함
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    if (init?.signal?.aborted) throw err;
    // 4xx 클라이언트 에러 — 재시도 무의미
    if (err instanceof ApiError && err.status >= 400 && err.status < 500) throw err;
    if (retries <= 0) throw err;
    // 짧은 대기 후 재시도
    await new Promise((r) => setTimeout(r, 500));
    return requestWithRetry<T>(path, init, retries - 1);
  }
}

// ── Screening ──

export function createScreening(input: ScreeningInput) {
  return request<ScreeningResponse>("/api/screening", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getScreening(id: string, options?: { signal?: AbortSignal }) {
  return requestWithRetry<ScreeningResponse>(`/api/screening/${id}`, {
    signal: options?.signal,
  });
}

export function listScreenings() {
  return request<ScreeningSummary[]>("/api/screening");
}

// ── Data Status ──

export function getDataStatus(
  lng = 127.49,
  lat = 37.49,
) {
  const params = new URLSearchParams({
    lng: String(lng),
    lat: String(lat),
  });
  return request<DataStatusResponse>(`/api/data-status?${params}`);
}

export function getScreeningDataStatus(
  screeningId: string,
  options?: { signal?: AbortSignal },
) {
  return requestWithRetry<ScreeningDataStatusResponse>(
    `/api/data-status/${screeningId}`,
    { signal: options?.signal },
  );
}

export function getConnectors() {
  return request<ConnectorListResponse>("/api/data-status/connectors");
}

// ── Evaluation ──

export function evaluateScreening(screeningId: string, options?: { signal?: AbortSignal; force?: boolean }) {
  return requestWithRetry<EvaluationResponse>(`/api/screening/${screeningId}/evaluate`, {
    method: "POST",
    body: JSON.stringify({ force: options?.force ?? false }),
    signal: options?.signal,
  });
}

export function getRegulations(screeningId: string) {
  return request<RegulationMatch[]>(`/api/screening/${screeningId}/regulations`);
}

export function getChecklist(screeningId: string, options?: { signal?: AbortSignal }) {
  return requestWithRetry<ChecklistResponse>(`/api/screening/${screeningId}/checklist`, {
    signal: options?.signal,
  });
}

// ── Cases ──

export function searchCases(params: {
  project_type?: string;
  location_type?: string;
  keyword?: string;
  tags?: string;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params.project_type) searchParams.set("project_type", params.project_type);
  if (params.location_type) searchParams.set("location_type", params.location_type);
  if (params.keyword) searchParams.set("keyword", params.keyword);
  if (params.tags) searchParams.set("tags", params.tags);
  if (params.limit) searchParams.set("limit", String(params.limit));
  return request<CaseSearchResponse>(`/api/cases?${searchParams}`);
}

export function getSimilarCases(screeningId: string, limit = 5) {
  return request<CaseSearchResponse>(
    `/api/screening/${screeningId}/similar-cases`,
    { method: "POST", body: JSON.stringify({ limit }) },
  );
}

// ── LLM Interpretation ──

export function getInterpretation(screeningId: string) {
  return request<InterpretationResponse>(
    `/api/screening/${screeningId}/interpret`,
    { method: "POST" },
  );
}

// ── Reports ──

export async function downloadReport(
  screeningId: string,
  reportType: "brief" | "full" | "checklist",
) {
  const res = await fetch(`${API_BASE}/api/screening/${screeningId}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ report_type: reportType }),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.blob();
}

// ── Compare ──

export function compareScreenings(screeningIds: string[]) {
  return request<CompareResponse>("/api/screening/compare", {
    method: "POST",
    body: JSON.stringify({ screening_ids: screeningIds }),
  });
}

export async function downloadCompareReport(screeningIds: string[]) {
  const res = await fetch(`${API_BASE}/api/screening/compare/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ screening_ids: screeningIds }),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.blob();
}

// ── Patterns ──

export function getPatterns(projectType: string) {
  return request<import("@/types/patterns").PatternResponse>(
    `/api/patterns/${projectType}`,
  );
}

export function getPrediction(
  projectType: string,
  locationString?: string,
  options?: { signal?: AbortSignal },
) {
  const params = new URLSearchParams();
  if (locationString) params.set("location_type", locationString);
  const qs = params.toString();
  return requestWithRetry<import("@/types/patterns").PredictionResponse>(
    `/api/patterns/${projectType}/predict${qs ? `?${qs}` : ""}`,
    { signal: options?.signal },
  );
}

export function getPatternSummary() {
  return request<import("@/types/patterns").OverallPatternSummary>(
    "/api/patterns",
  );
}

// ── Draft Copilot ──

export function generateDraft(
  screeningId: string,
  body: import("@/types/draft").DraftRequest = {},
) {
  return request<import("@/types/draft").DraftFullResponse>(
    `/api/screening/${screeningId}/draft`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function generateSectionDraft(
  screeningId: string,
  sectionId: string,
  body: import("@/types/draft").DraftRequest = {},
) {
  return request<import("@/types/draft").DraftSection>(
    `/api/screening/${screeningId}/draft/${sectionId}`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function getDraftTemplate() {
  return request<import("@/types/draft").TemplateResponse>(
    "/api/draft/template",
  );
}

// ── Review Prediction + Quality Check ──

export function predictReview(
  screeningId: string,
  body: import("@/types/review").ReviewPredictionRequest = {},
  options?: { signal?: AbortSignal },
) {
  return requestWithRetry<import("@/types/review").ReviewPredictionResponse>(
    `/api/screening/${screeningId}/predict-review`,
    { method: "POST", body: JSON.stringify(body), signal: options?.signal },
  );
}

export function qualityCheck(
  screeningId: string,
  body: import("@/types/review").QualityCheckRequest = {},
  options?: { signal?: AbortSignal },
) {
  return requestWithRetry<import("@/types/review").QualityCheckResponse>(
    `/api/screening/${screeningId}/quality-check`,
    { method: "POST", body: JSON.stringify(body), signal: options?.signal },
  );
}

// ── RAG ──

export interface RagSource {
  report_id: string;
  project_name: string;
  project_type: string;
  year: string;
  chapter: string;
  section: string;
  page_range: string;
  similarity: number;
  excerpt: string;
}

export interface RagResponse {
  answer: string;
  sources: RagSource[];
  total_indexed: number;
  generated_at?: string;
  disclaimer: string;
}

export function queryRag(question: string, projectType?: string) {
  return request<RagResponse>("/api/rag/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      n_results: 5,
      project_type: projectType,
    }),
  });
}

// ── Auth ──

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const tokens = await request<AuthTokens>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
  }
  return tokens;
}

export async function register(email: string, password: string, name?: string) {
  return request<{ id: string; email: string; name: string; role: string }>(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify({ email, password, name }) },
  );
}

export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  }
}

// ── Health ──

export function getHealth() {
  return request<{ status: string; database: string; demo_mode: boolean }>(
    "/health",
  );
}

// ── Admin: Law Status ──

export interface LawStatusItem {
  law_name: string;
  system_version: string;
  last_amendment: string | null;
  checked_at: string | null;
  is_outdated: boolean;
  acknowledged: boolean;
}

export interface LawStatusResponse {
  laws: LawStatusItem[];
  has_outdated: boolean;
  total: number;
}

export function getLawStatus() {
  return request<LawStatusResponse>("/api/admin/law-status");
}

export function checkLaws() {
  return request<LawStatusResponse & { checked_at: string }>(
    "/api/admin/law-check",
    { method: "POST" },
  );
}

export function acknowledgeLaw(lawName: string) {
  return request<{ status: string; law_name: string }>(
    `/api/admin/law-acknowledge/${encodeURIComponent(lawName)}`,
    { method: "POST" },
  );
}

// ── Admin: Rules ──

export interface AdminRule {
  rule_id: string;
  title: string;
  severity: string;
  confidence: number;
  domain: string;
  human_review_required?: boolean;
  legal_basis?: string;
  condition?: Record<string, unknown>;
}

export interface AdminRulesResponse {
  total: number;
  domains: string[];
  rules_by_domain: Record<string, AdminRule[]>;
  rules: AdminRule[];
}

export function getAdminRules(domain?: string) {
  const params = domain ? `?domain=${encodeURIComponent(domain)}` : "";
  return request<AdminRulesResponse>(`/api/admin/rules${params}`);
}

export function getAdminRule(ruleId: string) {
  return request<{ rule: Record<string, unknown>; yaml_source: string }>(
    `/api/admin/rules/${ruleId}`,
  );
}

export function updateAdminRule(
  ruleId: string,
  body: {
    severity?: string;
    confidence?: number;
    condition_value?: unknown;
    human_review_required?: boolean;
  },
) {
  return request<{ status: string; rule_id: string; changes: Record<string, unknown> }>(
    `/api/admin/rules/${ruleId}`,
    { method: "PUT", body: JSON.stringify(body) },
  );
}
