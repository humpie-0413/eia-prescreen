"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import { ChartEmptyState } from "./chart-empty-state";

interface ReviewBarDatum {
  category: string;
  probability_pct: number;
}

interface ReviewBarChartProps {
  data: ReviewBarDatum[];
}

export function ReviewBarChart({ data }: ReviewBarChartProps) {
  const sorted = [...(data ?? [])].sort(
    (a, b) => b.probability_pct - a.probability_pct,
  );

  if (sorted.length === 0) {
    return <ChartEmptyState message="검토의견 예측 데이터 없음" />;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(sorted.length * 36, 80)} minWidth={1}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 0, right: 40, top: 4, bottom: 4 }}>
        <XAxis type="number" domain={[0, 100]} hide />
        <YAxis
          type="category"
          dataKey="category"
          width={50}
          tick={{ fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Bar
          dataKey="probability_pct"
          radius={[0, 4, 4, 0]}
          barSize={18}
        >
          {sorted.map((entry) => (
            <Cell
              key={entry.category}
              fill="var(--color-chart-primary)"
              data-testid={`review-bar-${entry.category}`}
            />
          ))}
          <LabelList
            dataKey="probability_pct"
            position="right"
            formatter={(v: string | number | boolean | null | undefined) => `${v ?? 0}%`}
            style={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
