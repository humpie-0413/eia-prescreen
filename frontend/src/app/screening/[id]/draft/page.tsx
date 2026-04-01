"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ChevronDown } from "lucide-react";
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
import { generateDraft } from "@/lib/api";
import type { DraftFullResponse, DraftSection } from "@/types/draft";

/* ─────────────────────────────────────────────
   Badge Component
   ───────────────────────────────────────────── */

const BADGE_STYLES: Record<string, string> = {
  "자동 생성":
    "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400",
  "현장조사 필요":
    "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
  "전문가 검토 필요":
    "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400",
};

const SectionBadge = ({ badge }: { badge: string }) => (
  <Badge
    variant="outline"
    className={`border-0 text-xs ${BADGE_STYLES[badge] ?? "bg-muted text-muted-foreground"}`}
  >
    {badge}
  </Badge>
);

/* ─────────────────────────────────────────────
   Markdown-like Renderer (simple)
   ───────────────────────────────────────────── */

function renderMarkdown(content: string) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const key = `line-${i}`;

    if (line.startsWith("## ")) {
      elements.push(
        <h2 key={key} className="text-lg font-bold mt-4 mb-2">
          {line.slice(3)}
        </h2>,
      );
    } else if (line.startsWith("### ")) {
      elements.push(
        <h3 key={key} className="text-base font-semibold mt-3 mb-1.5">
          {line.slice(4)}
        </h3>,
      );
    } else if (line.startsWith("> ")) {
      const text = line.slice(2);
      const isWarning =
        text.includes("[현장조사 필요]") ||
        text.includes("[전문가 검토 필요]") ||
        text.includes("[자동 생성]");
      elements.push(
        <blockquote
          key={key}
          className={`border-l-4 pl-3 py-1 my-2 text-sm ${
            isWarning
              ? "border-orange-400 bg-orange-50 dark:bg-orange-950/30 text-orange-800 dark:text-orange-300"
              : "border-muted-foreground/30 bg-muted/30 text-muted-foreground"
          }`}
        >
          {renderInlineMarkdown(text)}
        </blockquote>,
      );
    } else if (line.startsWith("| ") && line.includes("|")) {
      // Collect table rows
      const tableRows: string[] = [line];
      let j = i + 1;
      while (j < lines.length && lines[j].startsWith("|")) {
        tableRows.push(lines[j]);
        j++;
      }
      i = j - 1;

      const dataRows = tableRows.filter((r) => !r.match(/^\|[\s-|]+\|$/));
      if (dataRows.length > 0) {
        const headerCells = dataRows[0]
          .split("|")
          .filter((c) => c.trim())
          .map((c) => c.trim());
        const bodyRows = dataRows.slice(1).map((r) =>
          r
            .split("|")
            .filter((c) => c.trim())
            .map((c) => c.trim()),
        );

        elements.push(
          <div key={key} className="overflow-x-auto my-2">
            <table className="text-sm border-collapse w-full">
              <thead>
                <tr className="border-b border-border">
                  {headerCells.map((cell, ci) => (
                    <th
                      key={ci}
                      className="text-left py-1.5 px-2 font-semibold text-foreground"
                    >
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((row, ri) => (
                  <tr key={ri} className="border-b border-border/50">
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="py-1.5 px-2 text-muted-foreground"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
      }
    } else if (line.startsWith("- ")) {
      elements.push(
        <li
          key={key}
          className="ml-4 text-sm text-muted-foreground list-disc"
        >
          {renderInlineMarkdown(line.slice(2))}
        </li>,
      );
    } else if (line.match(/^\d+\.\s/)) {
      elements.push(
        <li
          key={key}
          className="ml-4 text-sm text-muted-foreground list-decimal"
        >
          {renderInlineMarkdown(line.replace(/^\d+\.\s/, ""))}
        </li>,
      );
    } else if (line.trim() === "") {
      elements.push(<div key={key} className="h-2" />);
    } else {
      elements.push(
        <p key={key} className="text-sm text-foreground leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>,
      );
    }
  }

  return <div className="space-y-0">{elements}</div>;
}

function renderInlineMarkdown(text: string): React.ReactNode {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

/* ─────────────────────────────────────────────
   Section Card Component
   ───────────────────────────────────────────── */

const DraftSectionCard = ({
  section,
  isExpanded,
  onToggle,
}: {
  section: DraftSection;
  isExpanded: boolean;
  onToggle: () => void;
}) => (
  <Card className="transition-shadow hover:shadow-md">
    <CardHeader
      className="cursor-pointer select-none"
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onToggle();
        }
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-muted-foreground font-mono shrink-0">
            {section.section_id}
          </span>
          <CardTitle className="text-base truncate">{section.title}</CardTitle>
          <SectionBadge badge={section.badge} />
        </div>
        <ChevronDown
          className={`size-4 shrink-0 text-muted-foreground transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
        />
      </div>
      <p className="text-xs text-muted-foreground">{section.chapter}</p>
    </CardHeader>
    {isExpanded && (
      <CardContent className="pt-0 border-t border-border">
        <div className="pt-4">{renderMarkdown(section.content)}</div>
      </CardContent>
    )}
  </Card>
);

/* ─────────────────────────────────────────────
   Summary Stats
   ───────────────────────────────────────────── */

const DraftSummary = ({ sections, totalSections }: { sections: DraftSection[]; totalSections: number }) => {
  const autoCount = sections.filter((s) => s.badge === "자동 생성").length;
  const fieldCount = sections.filter((s) => s.badge === "현장조사 필요").length;
  const expertCount = sections.filter(
    (s) => s.badge === "전문가 검토 필요",
  ).length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {totalSections}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">전체 섹션</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-teal-700 dark:text-teal-400">
            {autoCount}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">자동 생성</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {fieldCount}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">현장조사 필요</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 px-4">
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {expertCount}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            전문가 검토 필요
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

/* ─────────────────────────────────────────────
   Page Component
   ───────────────────────────────────────────── */

export default function DraftPage() {
  const { id } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftData, setDraftData] = useState<DraftFullResponse | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(),
  );
  const [expandAll, setExpandAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function fetchDraft() {
      setLoading(true);
      setError(null);
      try {
        const result = await generateDraft(id, {});
        if (!cancelled) setDraftData(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "초안 생성 실패");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchDraft();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-4">
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="card" count={3} />
      </div>
    );
  }

  if (error || !draftData) {
    return (
      <ErrorState
        message={error || "데이터를 불러올 수 없습니다."}
        onRetry={() => window.location.reload()}
      />
    );
  }

  const sections = draftData.sections;
  const projectName = draftData.project_info?.project_name ?? "";

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    if (expandAll) {
      setExpandedSections(new Set());
    } else {
      setExpandedSections(new Set(sections.map((s) => s.section_id)));
    }
    setExpandAll(!expandAll);
  };

  // Group by chapter
  const chapters = new Map<string, DraftSection[]>();
  for (const section of sections) {
    const list = chapters.get(section.chapter) ?? [];
    list.push(section);
    chapters.set(section.chapter, list);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="max-w-5xl mx-auto p-4 md:p-8 space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">평가서 초안 생성</h1>
            <Badge
              variant="outline"
              className="border-0 bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400 text-xs"
            >
              AI 생성 참고용
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {projectName} | 스크리닝 ID: {id}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExpandAll}>
            {expandAll ? "모두 접기" : "모두 펼치기"}
          </Button>
        </div>
      </div>

      <Separator />

      {/* Disclaimer Banner */}
      <div className="rounded-lg border border-yellow-300 bg-yellow-50 dark:bg-yellow-950/30 dark:border-yellow-700 p-4">
        <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
          {draftData.disclaimer}
        </p>
        <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">
          환경영향평가서의 법적 요건을 충족하기 위해서는 현장조사 결과, 전문가
          판단, 정밀 모델링 결과 등이 반드시 반영되어야 합니다.
        </p>
      </div>

      {/* Summary */}
      <DraftSummary sections={sections} totalSections={draftData.total_sections} />

      {/* Sections grouped by chapter */}
      {Array.from(chapters.entries()).map(([chapter, chSections]) => (
        <div key={chapter} className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground border-l-4 border-teal-500 pl-3">
            {chapter}
          </h2>
          {chSections.map((section) => (
            <DraftSectionCard
              key={section.section_id}
              section={section}
              isExpanded={expandedSections.has(section.section_id)}
              onToggle={() => toggleSection(section.section_id)}
            />
          ))}
        </div>
      ))}

      {/* Footer disclaimer */}
      <Separator />
      <p className="text-xs text-muted-foreground text-center">
        * 이 초안은 과거 환경영향평가 데이터와 규칙 엔진 분석을 기반으로
        자동 생성되었습니다. 법적·행정적 효력이 없으며, 전문가 검토가
        필수적입니다.
      </p>
    </motion.div>
  );
}
