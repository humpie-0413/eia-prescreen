"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { EmptyState } from "@/components/feedback";
import {
  searchCases,
  getSimilarCases,
  getInterpretation,
  downloadReport,
} from "@/lib/api";
import type { CaseResult, InterpretationResponse } from "@/types/screening";

// ── Helpers ──

const PROJECT_TYPES = [
  "도로",
  "주거단지",
  "발전소",
  "공장",
  "산업단지",
  "관광단지",
  "항만",
  "철도",
  "댐·저수지",
  "기타",
];

const LOCATION_TYPES = [
  "산지 인접",
  "하천 인접",
  "해안 인접",
  "도심",
  "농경지",
  "습지 인접",
  "보호구역 인접",
  "기타",
];

function consultationColor(result: string) {
  if (result === "동의") return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
  if (result === "조건부 동의") return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
  if (result === "부동의") return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
  return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
}

// ── Main Page ──

export default function CasesPage() {
  const { id } = useParams<{ id: string }>();

  const [activeTab, setActiveTab] = useState<"cases" | "reports" | "interpret">("cases");

  // Cases state
  const [cases, setCases] = useState<CaseResult[]>([]);
  const [casesTotal, setCasesTotal] = useState(0);
  const [casesLoading, setCasesLoading] = useState(false);
  const [casesError, setCasesError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);

  // Filters
  const [filterProjectType, setFilterProjectType] = useState("");
  const [filterLocationType, setFilterLocationType] = useState("");
  const [filterKeyword, setFilterKeyword] = useState("");

  // Detail modal
  const [selectedCase, setSelectedCase] = useState<CaseResult | null>(null);

  // Reports state
  const [downloadingReport, setDownloadingReport] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  // Interpretation state
  const [interpretation, setInterpretation] = useState<InterpretationResponse | null>(null);
  const [interpretLoading, setInterpretLoading] = useState(false);
  const [interpretError, setInterpretError] = useState<string | null>(null);

  // ── Cases handlers ──

  async function handleSearchCases() {
    setCasesLoading(true);
    setCasesError(null);
    try {
      const res = await searchCases({
        project_type: filterProjectType || undefined,
        location_type: filterLocationType || undefined,
        keyword: filterKeyword || undefined,
        limit: 20,
      });
      setCases(res.cases);
      setCasesTotal(res.total);
      setHasFetched(true);
    } catch (err) {
      setCasesError(err instanceof Error ? err.message : "검색에 실패했습니다.");
    } finally {
      setCasesLoading(false);
    }
  }

  async function handleSimilarCases() {
    setCasesLoading(true);
    setCasesError(null);
    try {
      const res = await getSimilarCases(id, 10);
      setCases(res.cases);
      setCasesTotal(res.total);
      setHasFetched(true);
    } catch (err) {
      setCasesError(err instanceof Error ? err.message : "유사사례 조회에 실패했습니다.");
    } finally {
      setCasesLoading(false);
    }
  }

  // ── Report handlers ──

  async function handleDownload(reportType: "brief" | "full" | "checklist", label: string) {
    setDownloadingReport(reportType);
    setReportError(null);
    try {
      const blob = await downloadReport(id, reportType);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}_${reportType}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : `${label} 다운로드에 실패했습니다.`);
    } finally {
      setDownloadingReport(null);
    }
  }

  // ── Interpretation handlers ──

  async function handleInterpret() {
    setInterpretLoading(true);
    setInterpretError(null);
    try {
      const res = await getInterpretation(id);
      setInterpretation(res);
    } catch (err) {
      setInterpretError(err instanceof Error ? err.message : "AI 해석 생성에 실패했습니다.");
    } finally {
      setInterpretLoading(false);
    }
  }

  // ── Tab button style helper ──

  function tabClass(tab: string) {
    const base =
      "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors focus:outline-none";
    if (activeTab === tab) {
      return `${base} bg-card text-teal-700 dark:text-teal-400 border border-b-0 border-border`;
    }
    return `${base} text-muted-foreground hover:text-foreground`;
  }

  return (
    <motion.div
      className="max-w-6xl mx-auto p-4 md:p-8 space-y-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">유사사례 & 보고서</h1>
        <p className="text-sm text-muted-foreground mt-1">
          스크리닝 ID: <span className="font-mono">{id}</span>
        </p>
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b border-border">
          <button className={tabClass("cases")} onClick={() => setActiveTab("cases")}>
            유사사례
          </button>
          <button className={tabClass("reports")} onClick={() => setActiveTab("reports")}>
            보고서 다운로드
          </button>
          <button className={tabClass("interpret")} onClick={() => setActiveTab("interpret")}>
            AI 해석
          </button>
        </div>

        {/* ───────── Cases Tab ───────── */}
        {activeTab === "cases" && (
          <div className="mt-6 space-y-6">
            {/* Filters */}
            <div className="bg-card border border-border rounded-lg p-4 space-y-4">
              <h3 className="text-sm font-semibold text-foreground/80">
                사례 검색 필터
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    사업유형
                  </label>
                  <select
                    value={filterProjectType}
                    onChange={(e) => setFilterProjectType(e.target.value)}
                    className="w-full rounded-md border border-border bg-background text-sm text-foreground px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="">전체</option>
                    {PROJECT_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    입지유형
                  </label>
                  <select
                    value={filterLocationType}
                    onChange={(e) => setFilterLocationType(e.target.value)}
                    className="w-full rounded-md border border-border bg-background text-sm text-foreground px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="">전체</option>
                    {LOCATION_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    키워드
                  </label>
                  <input
                    type="text"
                    value={filterKeyword}
                    onChange={(e) => setFilterKeyword(e.target.value)}
                    placeholder="키워드 검색..."
                    onKeyDown={(e) => e.key === "Enter" && handleSearchCases()}
                    className="w-full rounded-md border border-border bg-background text-sm text-foreground px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder:text-gray-400"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <button
                    onClick={handleSearchCases}
                    disabled={casesLoading}
                    className="flex-1 rounded-md bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white text-sm font-medium px-4 py-2 transition-colors"
                  >
                    {casesLoading ? "검색 중..." : "검색"}
                  </button>
                  <button
                    onClick={handleSimilarCases}
                    disabled={casesLoading}
                    className="flex-1 rounded-md bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm font-medium px-4 py-2 transition-colors"
                  >
                    {casesLoading ? "조회 중..." : "유사사례"}
                  </button>
                </div>
              </div>
            </div>

            {/* Error */}
            {casesError && (
              <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
                {casesError}
              </div>
            )}

            {/* Results header */}
            {hasFetched && (
              <p className="text-sm text-muted-foreground">
                총 <span className="font-semibold text-foreground">{casesTotal}</span>건 조회됨
              </p>
            )}

            {/* Loading */}
            {casesLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
              </div>
            )}

            {/* Case cards grid */}
            {!casesLoading && cases.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {cases.map((c) => (
                  <button
                    key={c.case_id}
                    onClick={() => setSelectedCase(c)}
                    className="text-left bg-card border border-border rounded-lg p-4 hover:shadow-md hover:border-teal-300 dark:hover:border-teal-600 transition-all focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="inline-block text-xs font-mono bg-muted text-muted-foreground px-2 py-0.5 rounded">
                            {c.case_id}
                          </span>
                          <span className="text-sm font-medium text-foreground">
                            {c.project_type}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {c.region}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-foreground/70 line-clamp-3">
                          {c.summary}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {c.tags.map((tag) => (
                            <span
                              key={tag}
                              className="inline-block text-xs bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 px-2 py-0.5 rounded-full"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <span
                          className={`inline-block text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${consultationColor(c.consultation_result)}`}
                        >
                          {c.consultation_result}
                        </span>
                        {c.similarity_score != null && (
                          <div className="mt-2 text-right">
                            <span className="text-xs text-muted-foreground/70">
                              유사도 {Math.round(c.similarity_score * 100)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Empty state */}
            {!casesLoading && hasFetched && cases.length === 0 && (
              <EmptyState
                icon={Search}
                title="검색 결과가 없습니다"
                description="다른 검색어나 필터를 시도해보세요."
              />
            )}

            {/* Initial state */}
            {!hasFetched && !casesLoading && (
              <div className="text-center py-12">
                <p className="text-sm text-muted-foreground">
                  검색 버튼 또는 유사사례 버튼을 눌러 사례를 조회하세요.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ───────── Reports Tab ───────── */}
        {activeTab === "reports" && (
          <div className="mt-6 space-y-4">
            {reportError && (
              <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
                {reportError}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Brief */}
              <div className="bg-card border border-border rounded-lg p-5 flex flex-col">
                <div className="text-2xl mb-3">📋</div>
                <h3 className="text-sm font-semibold text-foreground">
                  1p 브리프
                </h3>
                <p className="text-xs text-muted-foreground mt-1 flex-1">
                  1페이지 사전검토 요약 브리프. 주요 리스크와 규제 사항을 한눈에 확인할 수 있습니다.
                </p>
                <button
                  onClick={() => handleDownload("brief", "1p 브리프")}
                  disabled={downloadingReport === "brief"}
                  className="mt-4 w-full rounded-md bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white text-sm font-medium px-4 py-2 transition-colors flex items-center justify-center gap-2"
                >
                  {downloadingReport === "brief" ? (
                    <>
                      <span className="animate-spin inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                      다운로드 중...
                    </>
                  ) : (
                    "PDF 다운로드"
                  )}
                </button>
              </div>

              {/* Full report */}
              <div className="bg-card border border-border rounded-lg p-5 flex flex-col">
                <div className="text-2xl mb-3">📄</div>
                <h3 className="text-sm font-semibold text-foreground">
                  환경현황 요약
                </h3>
                <p className="text-xs text-muted-foreground mt-1 flex-1">
                  5~10페이지 환경현황 요약 보고서. 공간정보, 규제현황, 리스크 분석 결과를 포함합니다.
                </p>
                <button
                  onClick={() => handleDownload("full", "환경현황 요약")}
                  disabled={downloadingReport === "full"}
                  className="mt-4 w-full rounded-md bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white text-sm font-medium px-4 py-2 transition-colors flex items-center justify-center gap-2"
                >
                  {downloadingReport === "full" ? (
                    <>
                      <span className="animate-spin inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                      다운로드 중...
                    </>
                  ) : (
                    "PDF 다운로드"
                  )}
                </button>
              </div>

              {/* Checklist */}
              <div className="bg-card border border-border rounded-lg p-5 flex flex-col">
                <div className="text-2xl mb-3">✅</div>
                <h3 className="text-sm font-semibold text-foreground">
                  체크리스트
                </h3>
                <p className="text-xs text-muted-foreground mt-1 flex-1">
                  환경영향평가 사전검토 체크리스트 PDF. 항목별 점검 결과를 정리하여 제공합니다.
                </p>
                <button
                  onClick={() => handleDownload("checklist", "체크리스트")}
                  disabled={downloadingReport === "checklist"}
                  className="mt-4 w-full rounded-md bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 text-white text-sm font-medium px-4 py-2 transition-colors flex items-center justify-center gap-2"
                >
                  {downloadingReport === "checklist" ? (
                    <>
                      <span className="animate-spin inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                      다운로드 중...
                    </>
                  ) : (
                    "PDF 다운로드"
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ───────── AI Interpretation Tab ───────── */}
        {activeTab === "interpret" && (
          <div className="mt-6 space-y-6">
            {/* Generate button */}
            {!interpretation && !interpretLoading && (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground mb-4">
                  AI가 스크리닝 결과를 종합 분석하여 해석을 생성합니다.
                </p>
                <button
                  onClick={handleInterpret}
                  className="rounded-md bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium px-6 py-2.5 transition-colors"
                >
                  AI 해석 생성
                </button>
              </div>
            )}

            {/* Loading */}
            {interpretLoading && (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <div className="animate-spin rounded-full h-10 w-10 border-2 border-teal-600 border-t-transparent" />
                <p className="text-sm text-muted-foreground">
                  AI 해석을 생성하고 있습니다...
                </p>
              </div>
            )}

            {/* Error */}
            {interpretError && (
              <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
                {interpretError}
                <button
                  onClick={handleInterpret}
                  className="ml-3 underline hover:no-underline"
                >
                  다시 시도
                </button>
              </div>
            )}

            {/* Result */}
            {interpretation && !interpretLoading && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold bg-teal-100 dark:bg-teal-950 text-teal-700 dark:text-teal-300 px-2.5 py-1 rounded-full">
                    AI 생성
                  </span>
                  <span className="text-xs text-muted-foreground/70">
                    {interpretation.model}
                  </span>
                  <span className="text-xs text-muted-foreground/70">
                    {new Date(interpretation.generated_at).toLocaleString("ko-KR")}
                  </span>
                </div>

                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                    {interpretation.interpretation}
                  </p>
                </div>

                <div className="pt-3 border-t border-border">
                  <p className="text-xs text-muted-foreground/70 italic">
                    {interpretation.disclaimer}
                  </p>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleInterpret}
                    className="text-xs text-teal-600 dark:text-teal-400 hover:underline"
                  >
                    다시 생성
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ───────── Case Detail Modal ───────── */}
      {selectedCase && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={() => setSelectedCase(null)}
        >
          <div
            className="bg-card border border-border rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-border px-6 py-4 flex items-start justify-between gap-4 rounded-t-xl">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono bg-muted text-muted-foreground px-2 py-0.5 rounded">
                    {selectedCase.case_id}
                  </span>
                  <span
                    className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${consultationColor(selectedCase.consultation_result)}`}
                  >
                    {selectedCase.consultation_result}
                  </span>
                </div>
                <h2 className="mt-2 text-lg font-semibold text-foreground">
                  {selectedCase.project_type} — {selectedCase.region}
                </h2>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-muted-foreground hover:text-foreground text-xl leading-none flex-shrink-0 mt-1"
                aria-label="닫기"
              >
                &times;
              </button>
            </div>

            {/* Modal body */}
            <div className="px-6 py-5 space-y-5">
              {/* Info grid */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">사업유형</span>
                  <p className="font-medium text-foreground">{selectedCase.project_type}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">입지유형</span>
                  <p className="font-medium text-foreground">{selectedCase.location_type}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">권역</span>
                  <p className="font-medium text-foreground">{selectedCase.region}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">출처</span>
                  <p className="font-medium text-foreground truncate">{selectedCase.source_document}</p>
                </div>
              </div>

              {/* Summary */}
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  요약
                </h4>
                <p className="text-sm text-foreground/80 leading-relaxed">
                  {selectedCase.summary}
                </p>
              </div>

              {/* Key issues */}
              {selectedCase.key_issues.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    주요 쟁점
                  </h4>
                  <ul className="space-y-1">
                    {selectedCase.key_issues.map((issue, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                        <span className="text-orange-500 mt-0.5 flex-shrink-0">&#x2022;</span>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Remediation */}
              {selectedCase.remediation_required.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    저감 조치 요구사항
                  </h4>
                  <ul className="space-y-1">
                    {selectedCase.remediation_required.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                        <span className="text-blue-500 mt-0.5 flex-shrink-0">&#x2022;</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Public concerns */}
              {selectedCase.public_concerns.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    주민 의견 / 우려사항
                  </h4>
                  <ul className="space-y-1">
                    {selectedCase.public_concerns.map((concern, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                        <span className="text-yellow-500 mt-0.5 flex-shrink-0">&#x2022;</span>
                        {concern}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tags */}
              {selectedCase.tags.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    태그
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedCase.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-block text-xs bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 px-2.5 py-0.5 rounded-full"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Similarity score */}
              {selectedCase.similarity_score != null && (
                <div className="pt-3 border-t border-border">
                  <span className="text-xs text-muted-foreground/70">
                    유사도 점수: {Math.round(selectedCase.similarity_score * 100)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
