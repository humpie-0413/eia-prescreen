export default function ScreeningLoading() {
  return (
    <div className="p-6 space-y-6">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-7 w-48 bg-muted animate-pulse rounded" />
        <div className="h-4 w-72 bg-muted animate-pulse rounded" />
      </div>

      {/* Cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 bg-muted animate-pulse rounded-lg border border-border"
          />
        ))}
      </div>

      {/* Content skeleton */}
      <div className="h-64 bg-muted animate-pulse rounded-lg border border-border" />
    </div>
  );
}
