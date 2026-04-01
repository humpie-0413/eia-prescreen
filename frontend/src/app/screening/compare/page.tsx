"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { GitCompareArrows } from "lucide-react";
import { EmptyState } from "@/components/feedback";
import {
  listScreenings,
  compareScreenings,
  downloadCompareReport,
} from "@/lib/api";
import type {
  ScreeningSummary,
  CompareResponse,
  RiskComparisonRow,
  SiteRiskSummary,
} from "@/types/screening";

const SEVERITY_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: "bg-red-100 dark:bg-red-950", text: "text-red-700 dark:text-red-400", label: "Critical" },
  major:    { bg: "bg-orange-100 dark:bg-orange-950", text: "text-orange-700 dark:text-orange-400", label: "Major" },
  review:   { bg: "bg-yellow-100 dark:bg-yellow-950", text: "text-yellow-700 dark:text-yellow-400", label: "Review" },
  info:     { bg: "bg-blue-100 dark:bg-blue-950", text: "text-blue-700 dark:text-blue-400", label: "Info" },
};

const PROJECT_TYPE_LABELS: Record<string, string> = {
  road: "도로", housing: "주거", power_plant: "발전소", factory: "공장", other: "기타",
};

function SeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return <span className="text-muted-foreground text-xs">—</span>;
  const s = SEVERITY_STYLE[severity] ?? SEVERITY_STYLE.info;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

function SiteCard({ site, rank }: { site: SiteRiskSummary; rank: number }) {
  const isWinner = rank === 0;
  return (
    <div className={`rounded-lg border p-4 space-y-3 ${isWinner ? "border-emerald-500 dark:border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30" : "border-border bg-card"}`}>
      {isWinner && (
        <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
          <span>★</span> 상대적으로 낮은 리스크
        </div>
      )}
      <div>
        <p className="font-semibold text-sm truncate">{site.project_name}</p>
        <p className="text-xs text-muted-foreground">
          {PROJECT_TYPE_LABELS[site.project_type] ?? site.project_type}
          {site.address ? ` · ${site.address}` : ""}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {[
          { label: "Critical", count: site.critical_count, color: "text-red-600 dark:text-red-400" },
          { label: "Major",    count: site.major_count,    color: "text-orange-600 dark:text-orange-400" },
          { label: "Review",   count: site.review_count,   color: "text-yellow-600 dark:text-yellow-500" },
          { label: "Info",     count: site.info_count,     color: "text-blue-600 dark:text-blue-400" },
        ].map(({ label, count, color }) => (
          <div key={label} className="flex justify-between items-center rounded bg-muted/50 px-2 py-1 text-xs">
            <span className={`font-medium ${color}`}>{label}</span>
            <span className="font-bold">{count}</span>
          </div>
        ))}
      </div>
      <div className="text-xs text-muted-foreground border-t pt-2 flex justify-between">
        <span>총 리스크 {site.total_risks}건</span>
        <span>규제 {site.total_regulations}건 (인허가 {site.permit_required_count}건)</span>
      </div>
    </div>
  );
}

function RiskMatrix({ sites, matrix }: { sites: SiteRiskSummary[]; matrix: RiskComparisonRow[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/60">
            <th className="text-left px-3 py-2 font-medium text-xs w-24">규칙 ID</th>
            <th className="text-left px-3 py-2 font-medium text-xs">리스크 항목</th>
            {sites.map((s) => (
              <th key={s.screening_id} className="text-center px-3 py-2 font-medium text-xs max-w-32">
                <span className="block truncate">{s.project_name}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={row.rule_id} className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}>
              <td className="px-3 py-2 text-xs text-muted-foreground font-mono">{row.rule_id}</td>
              <td className="px-3 py-2 text-xs">{row.title}</td>
              {sites.map((s) => (
                <td key={s.screening_id} className="px-3 py-2 text-center">
                  <SeverityBadge severity={row.severity_by_site[s.screening_id] ?? null} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ComparePage() {
  const [screenings, setScreenings] = useState<ScreeningSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listScreenings()
      .then((data) => setScreenings(data.filter((s) => s.status === "evaluated")))
      .catch(() => setScreenings([]));
  }, []);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  }

  async function handleCompare() {
    if (selected.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await compareScreenings(selected);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "비교 실패");
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadPdf() {
    if (selected.length < 2) return;
    setLoadingPdf(true);
    try {
      const blob = await downloadCompareReport(selected);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "eia_comparison_report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF 다운로드 실패");
    } finally {
      setLoadingPdf(false);
    }
  }

  // Rank sites by risk score (lower = better)
  const rankedSites = result
    ? [...result.sites]
        .map((s) => ({
          site: s,
          score: s.critical_count * 10 + s.major_count * 5 + s.review_count * 2 + s.info_count,
        }))
        .sort((a, b) => a.score - b.score)
    : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="max-w-6xl mx-auto p-4 md:p-8 space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">부지 비교</h1>
        <p className="text-sm text-muted-foreground mt-1">
          평가 완료된 스크리닝 결과에서 최대 3개를 선택해 리스크를 비교합니다.
        </p>
      </div>

      {/* Site selector */}
      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">
            비교 부지 선택
            <span className="ml-2 text-xs text-muted-foreground">({selected.length}/3 선택됨)</span>
          </h2>
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              className="text-xs text-muted-foreground hover:text-foreground underline"
            >
              초기화
            </button>
          )}
        </div>

        {screenings.length === 0 ? (
          <EmptyState
            icon={GitCompareArrows}
            title="평가 완료된 스크리닝이 없습니다"
            description="먼저 새 검토를 실행해주세요."
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {screenings.map((s) => {
              const isSelected = selected.includes(s.id);
              const isDisabled = !isSelected && selected.length >= 3;
              return (
                <button
                  key={s.id}
                  onClick={() => toggleSelect(s.id)}
                  disabled={isDisabled}
                  className={`text-left rounded-lg border p-3 transition-colors text-sm ${
                    isSelected
                      ? "border-primary bg-primary/10"
                      : isDisabled
                      ? "border-border opacity-40 cursor-not-allowed"
                      : "border-border hover:border-primary/50 hover:bg-muted/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium truncate">{s.project_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {PROJECT_TYPE_LABELS[s.project_type] ?? s.project_type}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right text-xs">
                      {s.critical_count > 0 && (
                        <span className="text-red-600 dark:text-red-400 font-semibold">
                          C{s.critical_count}
                        </span>
                      )}
                      {s.major_count > 0 && (
                        <span className="ml-1 text-orange-600 dark:text-orange-400 font-semibold">
                          M{s.major_count}
                        </span>
                      )}
                    </div>
                  </div>
                  {isSelected && (
                    <div className="mt-1.5 flex items-center gap-1 text-xs text-primary font-medium">
                      <span>✓</span> 선택됨 ({selected.indexOf(s.id) + 1}번)
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button
            onClick={handleCompare}
            disabled={selected.length < 2 || loading}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {loading ? "비교 중..." : "비교 실행"}
          </button>
          {result && (
            <button
              onClick={handleDownloadPdf}
              disabled={loadingPdf}
              className="px-4 py-2 bg-muted text-foreground border border-border rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-muted/70 transition-colors"
            >
              {loadingPdf ? "생성 중..." : "📄 비교 보고서 PDF"}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div data-testid="error-state" className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Site summary cards */}
          <div>
            <h2 className="text-base font-semibold mb-3">부지별 리스크 요약</h2>
            <div className={`grid gap-4 ${result.sites.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
              {rankedSites.map(({ site }, rank) => (
                <SiteCard key={site.screening_id} site={site} rank={rank} />
              ))}
            </div>
          </div>

          {/* Recommendation */}
          <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/20 p-4">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 mb-2">
              종합 추천
            </h2>
            <p className="text-sm leading-relaxed">{result.recommendation}</p>
          </div>

          {/* Risk matrix */}
          <div>
            <h2 className="text-base font-semibold mb-3">
              리스크 비교 매트릭스
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                ({result.risk_matrix.length}개 항목)
              </span>
            </h2>
            {result.risk_matrix.length > 0 ? (
              <RiskMatrix sites={result.sites} matrix={result.risk_matrix} />
            ) : (
              <p className="text-sm text-muted-foreground">평가된 리스크가 없습니다.</p>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}
