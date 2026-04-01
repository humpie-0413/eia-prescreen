import type { Freshness } from "@/types/screening";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";

const FRESHNESS_CONFIG: Record<Freshness, { label: string; className: string; description: string }> = {
  live: {
    label: "Live",
    className: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
    description: "실시간 API 조회 데이터",
  },
  cached: {
    label: "Cached",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
    description: "캐시 스냅샷 데이터 (TTL 이내)",
  },
  stale: {
    label: "Stale",
    className: "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
    description: "오래된 캐시 데이터 (TTL 초과)",
  },
  demo: {
    label: "Demo",
    className: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400",
    description: "데모 시나리오 데이터",
  },
  unknown: {
    label: "N/A",
    className: "bg-gray-100 text-gray-500 dark:bg-gray-900 dark:text-gray-400",
    description: "데이터 상태 불명",
  },
};

interface FreshnessIndicatorProps {
  freshness: Freshness;
  snapshotAt?: string | null;
}

export function FreshnessIndicator({ freshness, snapshotAt }: FreshnessIndicatorProps) {
  const config = FRESHNESS_CONFIG[freshness];

  return (
    <Tooltip>
      <TooltipTrigger
        render={<Badge variant="outline" className={`border-0 text-[10px] px-1.5 py-0 cursor-default ${config.className}`} />}
      >
        {config.label}
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs max-w-60">
        <p>{config.description}</p>
        {snapshotAt && (
          <p className="mt-1 text-muted-foreground">
            기준: {new Date(snapshotAt).toLocaleString("ko-KR")}
          </p>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
