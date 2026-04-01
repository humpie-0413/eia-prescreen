import { BarChart3 } from "lucide-react";

interface ChartEmptyStateProps {
  message?: string;
}

export function ChartEmptyState({
  message = "데이터 없음",
}: ChartEmptyStateProps) {
  return (
    <div
      data-testid="chart-empty-state"
      className="flex flex-col items-center justify-center py-8 text-muted-foreground"
    >
      <BarChart3 className="size-10 mb-2 opacity-40" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
