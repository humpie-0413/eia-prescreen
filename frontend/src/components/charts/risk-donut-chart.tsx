"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChartEmptyState } from "./chart-empty-state";

interface DonutDatum {
  severity: string;
  count: number;
}

interface RiskDonutChartProps {
  data: DonutDatum[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--color-severity-critical)",
  major: "var(--color-severity-major)",
  review: "var(--color-severity-review)",
  info: "var(--color-severity-info)",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  major: "Major",
  review: "Review",
  info: "Info",
};

export function RiskDonutChart({ data }: RiskDonutChartProps) {
  const filtered = (data ?? []).filter((d) => d.count > 0);
  const total = filtered.reduce((sum, d) => sum + d.count, 0);

  if (filtered.length === 0) {
    return <ChartEmptyState message="리스크 데이터 없음" />;
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[160px] h-[160px]">
        <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
          <PieChart>
            <Pie
              data={filtered}
              dataKey="count"
              nameKey="severity"
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={2}
              strokeWidth={0}
            >
              {filtered.map((entry) => (
                <Cell
                  key={entry.severity}
                  fill={SEVERITY_COLORS[entry.severity] ?? "var(--color-severity-info)"}
                  data-testid={`risk-donut-${entry.severity}`}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold">{total}</span>
        </div>
      </div>
      <div className="flex gap-3 mt-2 flex-wrap justify-center">
        {filtered.map((d) => (
          <span key={d.severity} className="flex items-center gap-1 text-xs">
            <span
              className="inline-block size-2 rounded-full"
              style={{ backgroundColor: SEVERITY_COLORS[d.severity] }}
            />
            {SEVERITY_LABELS[d.severity] ?? d.severity} {d.count}
          </span>
        ))}
      </div>
    </div>
  );
}
