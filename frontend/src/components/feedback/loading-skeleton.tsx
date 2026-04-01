interface LoadingSkeletonProps {
  variant?: "card" | "list" | "chart";
  count?: number;
}

export function LoadingSkeleton({
  variant = "card",
  count = 1,
}: LoadingSkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  if (variant === "list") {
    return (
      <div data-testid="loading-skeleton" className="space-y-3">
        {items.map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="size-8 rounded-full bg-muted animate-pulse shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-3/4 rounded bg-muted animate-pulse" />
              <div className="h-2.5 w-1/2 rounded bg-muted animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div data-testid="loading-skeleton" className="space-y-2">
        <div className="h-4 w-24 rounded bg-muted animate-pulse" />
        <div className="flex items-end gap-2 h-32">
          {[40, 70, 55, 85, 30].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-muted animate-pulse"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  // card variant
  return (
    <div data-testid="loading-skeleton" className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((i) => (
        <div key={i} className="rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-5 w-16 rounded bg-muted animate-pulse" />
            <div className="h-4 w-20 rounded bg-muted animate-pulse" />
          </div>
          <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
          <div className="h-3 w-full rounded bg-muted animate-pulse" />
        </div>
      ))}
    </div>
  );
}
