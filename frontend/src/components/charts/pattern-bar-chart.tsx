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

interface PatternBarChartProps {
  data: Record<string, number>;
}

const PATTERN_COLORS: Record<string, string> = {
  "협의": "var(--color-severity-info)",
  "보완": "var(--color-severity-major)",
  "조건부협의": "var(--color-chart-primary)",
  "재검토": "var(--color-severity-critical)",
};

export function PatternBarChart({ data }: PatternBarChartProps) {
  const entries = Object.entries(data ?? {}).map(([name, value]) => ({
    name,
    value,
  }));

  if (entries.length === 0 || entries.every((e) => e.value === 0)) {
    return <ChartEmptyState message="패턴 데이터 없음" />;
  }

  return (
    <ResponsiveContainer width="100%" height={180} minWidth={1}>
      <BarChart data={entries} margin={{ top: 16, right: 4, bottom: 4, left: 4 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis hide domain={[0, 100]} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={36}>
          {entries.map((entry) => (
            <Cell
              key={entry.name}
              fill={PATTERN_COLORS[entry.name] ?? "var(--color-chart-primary)"}
              data-testid={`pattern-bar-${entry.name}`}
            />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            formatter={(v: string | number | boolean | null | undefined) => `${v ?? 0}%`}
            style={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
