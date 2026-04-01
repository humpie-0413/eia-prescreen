"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "@/components/risk/risk-badge";
import { EvidenceDrawer } from "@/components/risk/evidence-drawer";
import type { RiskCard, ChecklistSection, Severity } from "@/types/screening";
import { SEVERITY_CONFIG } from "@/types/screening";
import type { PredictedIssue, RemediationSuggestion } from "@/types/patterns";
import type { PredictedComment, QualityCheckItem } from "@/types/review";
import { evaluateScreening, getChecklist, predictReview, qualityCheck, getPrediction, getScreeningDataStatus, getScreening } from "@/lib/api";
import { TriangleAlert, CircleAlert, Info, CircleHelp } from "lucide-react";
import { RiskDonutChart } from "@/components/charts/risk-donut-chart";
import { ReviewBarChart } from "@/components/charts/review-bar-chart";
import { PatternBarChart } from "@/components/charts/pattern-bar-chart";
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useCountUpValue } from "@/hooks/use-count-up";
import { LawStatusBanner } from "@/components/admin/law-status-banner";

/* ─────────────────────────────────────────────
   Severity counts
   ───────────────────────────────────────────── */

const SEVERITY_ORDER: Severity[] = ["critical", "major", "review", "info"];

function countBySeverity(cards: RiskCard[]): Record<Severity, number> {
  const counts: Record<Severity, number> = {
    critical: 0,
    major: 0,
    review: 0,
    info: 0,
  };
  for (const c of cards) {
    counts[c.severity]++;
  }
  return counts;
}

/* ─────────────────────────────────────────────
   Severity icon SVGs
   ───────────────────────────────────────────── */

const SEVERITY_ICONS: Record<Severity, React.ReactNode> = {
  critical: <TriangleAlert className="size-5" />,
  major: <CircleAlert className="size-5" />,
  review: <Info className="size-5" />,
  info: <CircleHelp className="size-5" />,
};

/* ─────────────────────────────────────────────
   Inline Components
   ───────────────────────────────────────────── */

/** LLM interpretation card with teal accent */
const InterpretationCard = ({ interpretation }: { interpretation: string }) => (
  <Card className="border-t-4 border-t-teal-500">
    <CardHeader>
      <div className="flex items-center gap-2">
        <CardTitle className="text-base">AI 종합 해석</CardTitle>
        <Badge
          variant="outline"
          className="border-0 bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400 text-xs"
        >
          AI 생성 참고용
        </Badge>
      </div>
    </CardHeader>
    <CardContent>
      <div className="text-sm leading-relaxed text-foreground whitespace-pre-line">
        {interpretation}
      </div>
      <p className="mt-4 text-xs text-muted-foreground">
        * 이 해석은 AI가 생성한 참고용 정보이며, 법적·행정적 효력이 없습니다.
      </p>
    </CardContent>
  </Card>
);

/** Single severity summary card */
const SeveritySummaryCard = ({
  severity,
  count,
}: {
  severity: Severity;
  count: number;
}) => {
  const animatedCount = useCountUpValue(count);
  const config = SEVERITY_CONFIG[severity];
  return (
    <Card role="status" aria-label={`${config.label} ${count}건`}>
      <CardContent className="py-4 px-4 flex items-center gap-3">
        <div
          className={`flex items-center justify-center rounded-lg size-10 shrink-0 ${config.bg} ${config.color}`}
        >
          {SEVERITY_ICONS[severity]}
        </div>
        <div>
          <p className="text-2xl font-bold leading-none">{animatedCount}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {config.label}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

/** Severity summary grid */
const SeveritySummaryGrid = ({ cards }: { cards: RiskCard[] }) => {
  const counts = countBySeverity(cards);
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {SEVERITY_ORDER.map((sev) => (
        <SeveritySummaryCard key={sev} severity={sev} count={counts[sev]} />
      ))}
    </div>
  );
};

/** Individual risk card in the grid */
const RiskCardItem = ({
  card,
  onClick,
}: {
  card: RiskCard;
  onClick: () => void;
}) => (
  <Tooltip>
    <TooltipTrigger
      render={<div />}
      onClick={onClick}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`${SEVERITY_CONFIG[card.severity].label} 리스크: ${card.title}`}
    >
      <Card className="cursor-pointer transition-shadow hover:ring-2 hover:ring-teal-500/30 focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:outline-none">
        <CardContent className="py-4 px-5 space-y-2">
          <div className="flex items-center gap-2">
            <RiskBadge severity={card.severity} />
            <span className="text-xs text-muted-foreground font-mono">
              {card.rule_id}
            </span>
            {card.human_review_required && (
              <Badge
                variant="outline"
                className="border-0 bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400 text-xs ml-auto"
              >
                전문가 검토
              </Badge>
            )}
          </div>
          <p className="text-sm font-medium leading-snug">{card.title}</p>
          <p className="text-xs text-muted-foreground line-clamp-1">
            {card.rationale}
          </p>
        </CardContent>
      </Card>
    </TooltipTrigger>
    <TooltipContent data-testid="risk-tooltip" side="top">
      {card.rationale.length > 80
        ? card.rationale.slice(0, 80) + "\u2026"
        : card.rationale}
    </TooltipContent>
  </Tooltip>
);

/** Risk card grid */
const RiskCardGrid = ({
  cards,
  onCardClick,
}: {
  cards: RiskCard[];
  onCardClick: (card: RiskCard) => void;
}) => (
  <div>
    <h2 className="text-lg font-semibold mb-3">리스크 카드</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3" role="list" aria-label="리스크 카드 목록">
      {cards.map((card) => (
        <div key={card.id} role="listitem">
          <RiskCardItem
            card={card}
            onClick={() => onCardClick(card)}
          />
        </div>
      ))}
    </div>
  </div>
);

/** Priority review items */
const PriorityReviewItems = ({ cards }: { cards: RiskCard[] }) => {
  const sorted = [...cards].sort((a, b) => {
    const order: Record<Severity, number> = {
      critical: 0,
      major: 1,
      review: 2,
      info: 3,
    };
    return order[a.severity] - order[b.severity];
  });
  const topItems = sorted.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">우선 검토 항목</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3">
          {topItems.map((item, idx) => (
            <li key={item.id} className="flex gap-3">
              <span className="flex items-center justify-center size-6 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs font-bold shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium leading-snug">
                  {item.title}
                </p>
                {item.legal_basis && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {item.legal_basis}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
};

/** Checklist panel with interactive checkboxes */
const ChecklistPanel = ({
  sections,
  onToggle,
}: {
  sections: ChecklistSection[];
  onToggle: (sectionIdx: number, itemId: number) => void;
}) => {
  const PRIORITY_STYLE: Record<string, string> = {
    "필수": "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
    "권고": "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">현장조사 체크리스트</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {sections.map((section, sIdx) => (
          <div key={section.section_name}>
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-sm font-semibold">{section.section_name}</h3>
              <Badge
                variant="outline"
                className={`border-0 text-xs ${PRIORITY_STYLE[section.priority] ?? "bg-gray-100 text-gray-600"}`}
              >
                {section.priority}
              </Badge>
            </div>
            <div className="space-y-2">
              {section.items.map((item) => (
                <label
                  key={item.id}
                  className="flex items-start gap-3 rounded-lg border border-border p-3 cursor-pointer transition-colors hover:bg-muted/50"
                >
                  <input
                    type="checkbox"
                    checked={item.checked}
                    onChange={() => onToggle(sIdx, item.id)}
                    className="mt-0.5 size-4 shrink-0 accent-teal-600 rounded"
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm font-medium leading-snug ${
                        item.checked
                          ? "line-through text-muted-foreground"
                          : ""
                      }`}
                    >
                      {item.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {item.description}
                    </p>
                    {item.legal_basis && (
                      <p className="text-xs text-muted-foreground/70 mt-0.5">
                        {item.legal_basis}
                      </p>
                    )}
                  </div>
                </label>
              ))}
            </div>
            {sIdx < sections.length - 1 && <Separator className="mt-5" />}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

/** Data freshness stacked bar */
const FreshnessBar = ({
  summary,
  total,
}: {
  summary: Record<string, number>;
  total: number;
}) => {
  if (total === 0) return null;

  const segments = [
    { key: "live", label: "실시간", color: "bg-green-500" },
    { key: "demo", label: "데모", color: "bg-teal-500" },
    { key: "cached", label: "캐시", color: "bg-yellow-500" },
    { key: "stale", label: "오래됨", color: "bg-orange-500" },
    { key: "unknown", label: "없음", color: "bg-gray-400" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">데이터 신선도</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex h-3 rounded-full overflow-hidden">
          {segments.map((seg) => {
            const count = summary[seg.key] ?? 0;
            if (count === 0) return null;
            const pct = (count / total) * 100;
            return (
              <div
                key={seg.key}
                className={seg.color}
                style={{ width: `${pct}%` }}
                title={`${seg.label}: ${count}개`}
              />
            );
          })}
        </div>
        <div className="flex gap-4 flex-wrap">
          {segments.map((seg) => {
            const count = summary[seg.key] ?? 0;
            if (count === 0) return null;
            return (
              <div
                key={seg.key}
                className="flex items-center gap-1.5 text-xs text-muted-foreground"
              >
                <span
                  className={`inline-block size-2.5 rounded-full ${seg.color}`}
                />
                {seg.label} ({count})
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground">
          * 데모 모드에서는 mock 데이터를 사용합니다. 데이터 기준일자를 반드시
          확인하세요.
        </p>
      </CardContent>
    </Card>
  );
};

/* ─────────────────────────────────────────────
   Pattern Prediction Components
   ───────────────────────────────────────────── */

const CONSULTATION_BAR_COLORS: Record<string, string> = {
  "조건부협의": "bg-teal-500",
  "협의": "bg-green-500",
  "재검토": "bg-orange-500",
  "기타": "bg-gray-400",
};

/** Consultation result probability bar chart */
const ConsultationPredictionChart = ({
  prediction,
}: {
  prediction: Record<string, number>;
}) => {
  const entries = Object.entries(prediction).sort(([, a], [, b]) => b - a);
  return (
    <div className="space-y-2">
      {entries.map(([label, pct]) => (
        <div key={label} className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-foreground font-medium">{label}</span>
            <span className="text-muted-foreground">{pct}%</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${CONSULTATION_BAR_COLORS[label] ?? "bg-gray-400"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

/** Predicted issues list with probability bars */
const PredictedIssuesList = ({
  issues,
  totalInType,
  koreanType,
}: {
  issues: PredictedIssue[];
  totalInType: number;
  koreanType: string;
}) => (
  <Card>
    <CardHeader>
      <div className="flex items-center gap-2">
        <CardTitle className="text-base">빈출 지적항목</CardTitle>
        <Badge
          variant="outline"
          className="border-0 bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs"
        >
          {koreanType} {totalInType}건 분석
        </Badge>
      </div>
    </CardHeader>
    <CardContent className="space-y-3">
      {issues.map((item, idx) => (
        <div key={item.issue} className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center size-5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs font-bold shrink-0">
              {idx + 1}
            </span>
            <span className="text-sm font-medium flex-1">{item.issue}</span>
            <span className="text-sm font-semibold text-teal-700 dark:text-teal-400">
              {item.probability_pct}%
            </span>
          </div>
          <div className="ml-7">
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-teal-500 transition-all"
                style={{ width: `${item.probability_pct}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {item.description}
            </p>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

/** Remediation suggestions */
const RemediationPanel = ({
  suggestions,
}: {
  suggestions: RemediationSuggestion[];
}) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-base">과거 보완 패턴</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {suggestions.map((item) => (
        <div key={item.issue} className="space-y-1.5">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{item.issue}</p>
            <Badge
              variant="outline"
              className="border-0 bg-muted text-muted-foreground text-xs"
            >
              빈도 {Math.round(item.frequency * 100)}%
            </Badge>
          </div>
          <ul className="ml-4 space-y-0.5">
            {item.common_remediation.map((rem) => (
              <li key={rem} className="text-xs text-muted-foreground flex items-start gap-1.5">
                <span className="text-teal-500 mt-0.5 shrink-0">•</span>
                {rem}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </CardContent>
  </Card>
);

/** Pattern prediction section — combines all pattern components */
const PatternPredictionSection = ({
  predictedIssues,
  consultationPrediction,
  remediationSuggestions,
  totalInType,
  koreanType,
  avgReviewMonths,
  supplementPct,
}: {
  predictedIssues: PredictedIssue[];
  consultationPrediction: Record<string, number>;
  remediationSuggestions: RemediationSuggestion[];
  totalInType: number;
  koreanType: string;
  avgReviewMonths: number;
  supplementPct: number;
}) => (
  <div className="space-y-4">
    <div className="flex items-center gap-2">
      <h2 className="text-lg font-semibold">과거 데이터 기반 예측</h2>
      <Badge
        variant="outline"
        className="border-0 bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400 text-xs"
      >
        통계 참고용
      </Badge>
    </div>

    {/* Summary stats */}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {totalInType.toLocaleString()}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            과거 {koreanType} 사업 수
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {avgReviewMonths}개월
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            평균 검토 기간
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {supplementPct}%
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            보완 요구 확률
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {consultationPrediction["조건부협의"] ?? 0}%
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            조건부협의 확률
          </p>
        </CardContent>
      </Card>
    </div>

    {/* Consultation prediction + predicted issues side by side */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2">
        <PredictedIssuesList
          issues={predictedIssues}
          totalInType={totalInType}
          koreanType={koreanType}
        />
      </div>
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">예상 협의결과</CardTitle>
          </CardHeader>
          <CardContent>
            <ConsultationPredictionChart prediction={consultationPrediction} />
          </CardContent>
        </Card>
      </div>
    </div>

    {/* Remediation patterns */}
    <RemediationPanel suggestions={remediationSuggestions} />

    <p className="text-xs text-muted-foreground">
      * 이 예측은 과거 {totalInType.toLocaleString()}건의 환경영향평가 통계를 기반으로 한 참고 자료이며, 개별 사업의 실제 결과와 다를 수 있습니다.
    </p>
  </div>
);

/* ─────────────────────────────────────────────
   Review Prediction + Quality Check Components
   ───────────────────────────────────────────── */

const SEVERITY_COMMENT_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
  low: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
};

const SEVERITY_COMMENT_LABELS: Record<string, string> = {
  high: "높음",
  medium: "보통",
  low: "낮음",
};

/** 예상 검토의견 카드 */
const ReviewPredictionCard = ({
  comments,
}: {
  comments: PredictedComment[];
}) => (
  <Card>
    <CardHeader>
      <div className="flex items-center gap-2">
        <CardTitle className="text-base">예상 검토의견</CardTitle>
        <Badge
          variant="outline"
          className="border-0 bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400 text-xs"
        >
          AI 예측
        </Badge>
      </div>
    </CardHeader>
    <CardContent className="space-y-3">
      {comments.map((item, idx) => (
        <div
          key={item.category + idx}
          className="rounded-lg border border-border p-3 space-y-2"
        >
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="outline"
              className="border-0 bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs"
            >
              {item.category}
            </Badge>
            <Badge
              variant="outline"
              className={`border-0 text-xs ${SEVERITY_COMMENT_COLORS[item.severity] ?? ""}`}
            >
              {SEVERITY_COMMENT_LABELS[item.severity] ?? item.severity}
            </Badge>
            {item.risk_matched && (
              <Badge
                variant="outline"
                className="border-0 bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400 text-xs"
              >
                리스크 연동
              </Badge>
            )}
            <span className="ml-auto text-sm font-semibold text-teal-700 dark:text-teal-400">
              {item.probability_pct}%
            </span>
          </div>
          <p className="text-sm text-foreground leading-relaxed">
            {item.comment}
          </p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-teal-500 transition-all"
                style={{ width: `${item.probability_pct}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground shrink-0">
              과거 {item.past_count}/{item.total_past_cases}건
            </span>
          </div>
        </div>
      ))}
      <p className="text-xs text-muted-foreground">
        * 이 예측은 과거 통계 기반 참고 자료이며, 실제 검토의견과 다를 수 있습니다.
      </p>
    </CardContent>
  </Card>
);

const STATUS_COLORS: Record<string, string> = {
  pass: "text-green-600 dark:text-green-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  fail: "text-red-600 dark:text-red-400",
};

const STATUS_BG: Record<string, string> = {
  pass: "bg-green-100 dark:bg-green-950",
  warning: "bg-yellow-100 dark:bg-yellow-950",
  fail: "bg-red-100 dark:bg-red-950",
};

const STATUS_LABELS: Record<string, string> = {
  pass: "통과",
  warning: "주의",
  fail: "실패",
};

const STATUS_ICONS: Record<string, string> = {
  pass: "✓",
  warning: "!",
  fail: "✕",
};

/** 품질 체크 결과 카드 */
const QualityCheckCard = ({
  checks,
  score,
  overallStatus,
}: {
  checks: QualityCheckItem[];
  score: number;
  overallStatus: "pass" | "warning" | "fail";
}) => {
  const categories = [...new Set(checks.map((c) => c.category))];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle className="text-base">품질 체크 결과</CardTitle>
          <Badge
            variant="outline"
            className={`border-0 text-xs ${STATUS_BG[overallStatus]} ${STATUS_COLORS[overallStatus]}`}
          >
            {STATUS_LABELS[overallStatus]} ({score}점)
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Score bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">품질 점수</span>
            <span className={`font-semibold ${STATUS_COLORS[overallStatus]}`}>
              {score}/100
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                score >= 80
                  ? "bg-green-500"
                  : score >= 50
                    ? "bg-yellow-500"
                    : "bg-red-500"
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>

        {/* Check items by category */}
        {categories.map((cat) => (
          <div key={cat}>
            <h4 className="text-xs font-semibold text-muted-foreground mb-2">
              {cat}
            </h4>
            <div className="space-y-1.5">
              {checks
                .filter((c) => c.category === cat)
                .map((check) => (
                  <div
                    key={check.check_id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <span
                      className={`flex items-center justify-center size-5 rounded-full text-xs font-bold shrink-0 ${STATUS_BG[check.status]} ${STATUS_COLORS[check.status]}`}
                    >
                      {STATUS_ICONS[check.status]}
                    </span>
                    <span className="flex-1 truncate">{check.title}</span>
                    <Badge
                      variant="outline"
                      className={`border-0 text-xs shrink-0 ${STATUS_BG[check.status]} ${STATUS_COLORS[check.status]}`}
                    >
                      {STATUS_LABELS[check.status]}
                    </Badge>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

/* ─────────────────────────────────────────────
   Page Component
   ───────────────────────────────────────────── */

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();

  // Loading / error state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // API data states
  const [riskCards, setRiskCards] = useState<RiskCard[]>([]);
  const [checklistSections, setChecklistSections] = useState<ChecklistSection[]>([]);
  const [predictedComments, setPredictedComments] = useState<PredictedComment[]>([]);
  const [qualityChecks, setQualityChecks] = useState<QualityCheckItem[]>([]);
  const [qualityScore, setQualityScore] = useState(0);
  const [qualityStatus, setQualityStatus] = useState<"pass" | "warning" | "fail">("pass");
  const [predictedIssues, setPredictedIssues] = useState<PredictedIssue[]>([]);
  const [consultationPrediction, setConsultationPrediction] = useState<Record<string, number>>({});
  const [remediationSuggestions, setRemediationSuggestions] = useState<RemediationSuggestion[]>([]);
  const [patternTotal, setPatternTotal] = useState(0);
  const [patternType, setPatternType] = useState("");
  const [avgReviewMonths, setAvgReviewMonths] = useState(0);
  const [supplementPct, setSupplementPct] = useState(0);
  const [llmInterpretation, setLlmInterpretation] = useState("");
  const [freshnessSummary, setFreshnessSummary] = useState<Record<string, number>>({});

  // Drawer state
  const [drawerCard, setDrawerCard] = useState<RiskCard | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Fetch all data from backend APIs
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    async function fetchAll() {
      setLoading(true);
      setError(null);
      try {
        // Step 0: Get screening data to determine project type
        const screening = await getScreening(id, { signal });
        if (signal.aborted) return;
        const projectType = screening.project_type || "road";

        // All API calls in parallel — partial failure is OK
        const results = await Promise.allSettled([
          evaluateScreening(id, { signal }),              // 0
          getChecklist(id, { signal }),                   // 1
          predictReview(id, {}, { signal }),              // 2
          qualityCheck(id, {}, { signal }),               // 3
          getPrediction(projectType, undefined, { signal }), // 4
          getScreeningDataStatus(id, { signal }),         // 5
        ]);
        if (signal.aborted) return;

        // Evaluate
        if (results[0].status === "fulfilled") {
          const evalResult = results[0].value;
          const mappedCards: RiskCard[] = evalResult.risk_cards.map((c, idx) => ({
            id: String(idx + 1),
            rule_id: c.rule_id,
            rule_version: c.rule_version,
            title: c.title,
            severity: c.severity as Severity,
            rationale: c.rationale,
            evidence: c.evidence,
            next_action: c.next_action,
            legal_basis: c.legal_basis,
            confidence: c.confidence,
            human_review_required: c.human_review_required,
            trigger_dataset: c.trigger_dataset,
            source_snapshot_date: c.source_snapshot_date,
          }));
          setRiskCards(mappedCards);

          setLlmInterpretation(
            `${evalResult.summary.total_risks}건의 리스크가 식별되었습니다. ` +
            `Critical ${evalResult.summary.critical_count}건, Major ${evalResult.summary.major_count}건, ` +
            `Review ${evalResult.summary.review_count}건, Info ${evalResult.summary.info_count}건. ` +
            `규제 매칭 ${evalResult.summary.total_regulations}건 (인허가 필요 ${evalResult.summary.permit_required_count}건).`
          );
        }

        // Checklist
        if (results[1].status === "fulfilled") {
          const cl = results[1].value;
          setChecklistSections(
            cl.sections.map((s) => ({
              ...s,
              items: s.items.map((i) => ({ ...i })),
            })),
          );
        }

        // Review prediction
        if (results[2].status === "fulfilled") {
          const rp = results[2].value;
          setPredictedComments(rp.predicted_comments);
        }

        // Quality check
        if (results[3].status === "fulfilled") {
          const qc = results[3].value;
          setQualityChecks(qc.checks);
          setQualityScore(qc.score);
          setQualityStatus(qc.overall_status as "pass" | "warning" | "fail");
        }

        // Patterns prediction
        if (results[4].status === "fulfilled") {
          const pp = results[4].value;
          setPredictedIssues(pp.predicted_issues);
          setConsultationPrediction(pp.consultation_prediction);
          setRemediationSuggestions(pp.remediation_suggestions);
          setPatternTotal(pp.total_in_type);
          setPatternType(pp.korean_type);
          setAvgReviewMonths(pp.avg_review_months ?? 0);
          setSupplementPct(pp.supplement_required_pct ?? 0);
        }

        // Data status freshness
        if (results[5].status === "fulfilled") {
          const ds = results[5].value;
          setFreshnessSummary(ds.freshness_summary);
        }

        // If ALL failed, show error
        const allFailed = results.every((r) => r.status === "rejected");
        if (allFailed) {
          const firstErr = results[0].status === "rejected" ? results[0].reason : null;
          setError(firstErr instanceof Error ? firstErr.message : "데이터 로딩 실패");
        }
      } catch (err) {
        // AbortError는 탭 이동으로 인한 정상 취소 — 무시
        if (signal.aborted) return;
        setError(err instanceof Error ? err.message : "데이터 로딩 실패");
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    }
    fetchAll();
    return () => {
      controller.abort();
    };
  }, [id]);

  const handleCardClick = (card: RiskCard) => {
    setDrawerCard(card);
    setDrawerOpen(true);
  };

  const handleChecklistToggle = (sectionIdx: number, itemId: number) => {
    setChecklistSections((prev) =>
      prev.map((section, sIdx) => {
        if (sIdx !== sectionIdx) return section;
        return {
          ...section,
          items: section.items.map((item) =>
            item.id === itemId ? { ...item, checked: !item.checked } : item,
          ),
        };
      }),
    );
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="card" count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <motion.div
      className="max-w-6xl mx-auto p-4 md:p-8 space-y-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">결과 대시보드</h1>
          <p className="text-sm text-muted-foreground mt-1">
            스크리닝 ID: {id}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href={`/screening/${id}/map`}>
            <Button variant="outline" size="sm">
              지도 보기
            </Button>
          </Link>
          <Link href={`/screening/${id}/cases`}>
            <Button variant="outline" size="sm">
              유사사례
            </Button>
          </Link>
          <Link href={`/screening/${id}/data-status`}>
            <Button variant="outline" size="sm">
              데이터 현황
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Law Status Banner ── */}
      <LawStatusBanner />

      <Separator />

      {/* ── LLM Interpretation ── */}
      <InterpretationCard interpretation={llmInterpretation} />

      {/* ── Severity Summary ── */}
      <SeveritySummaryGrid cards={riskCards} />

      {/* ── Charts ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">리스크 분포</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskDonutChart
              data={SEVERITY_ORDER.map((sev) => ({
                severity: sev,
                count: countBySeverity(riskCards)[sev],
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">검토의견 예측</CardTitle>
          </CardHeader>
          <CardContent>
            <ReviewBarChart
              data={predictedComments.map((c) => ({
                category: c.category,
                probability_pct: c.probability_pct,
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">과거 패턴</CardTitle>
          </CardHeader>
          <CardContent>
            <PatternBarChart data={consultationPrediction} />
          </CardContent>
        </Card>
      </div>

      {/* ── Risk Card Grid ── */}
      <RiskCardGrid cards={riskCards} onCardClick={handleCardClick} />

      {/* ── Priority Review Items ── */}
      <PriorityReviewItems cards={riskCards} />

      <Separator />

      {/* ── Pattern Prediction ── */}
      <PatternPredictionSection
        predictedIssues={predictedIssues}
        consultationPrediction={consultationPrediction}
        remediationSuggestions={remediationSuggestions}
        totalInType={patternTotal}
        koreanType={patternType}
        avgReviewMonths={avgReviewMonths}
        supplementPct={supplementPct}
      />

      <Separator />

      {/* ── Review Prediction + Quality Check ── */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">검토의견 예측 & 품질 체크</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ReviewPredictionCard comments={predictedComments} />
          <QualityCheckCard
            checks={qualityChecks}
            score={qualityScore}
            overallStatus={qualityStatus}
          />
        </div>
      </div>

      <Separator />

      {/* ── Checklist Panel ── */}
      <ChecklistPanel
        sections={checklistSections}
        onToggle={handleChecklistToggle}
      />

      {/* ── Data Freshness Summary ── */}
      <FreshnessBar summary={freshnessSummary} total={Object.values(freshnessSummary).reduce((a, b) => a + b, 0)} />

      {/* ── Evidence Drawer ── */}
      <EvidenceDrawer
        card={drawerCard}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </motion.div>
  );
}
