import type { Severity } from "@/types/screening";
import { SEVERITY_CONFIG } from "@/types/screening";
import { Badge } from "@/components/ui/badge";

interface RiskBadgeProps {
  severity: Severity;
  className?: string;
}

export function RiskBadge({ severity, className }: RiskBadgeProps) {
  const config = SEVERITY_CONFIG[severity];

  return (
    <Badge
      variant="outline"
      className={`${config.bg} ${config.color} border-0 ${className ?? ""}`}
      role="status"
      aria-label={`리스크 등급: ${config.label}`}
    >
      {config.label}
    </Badge>
  );
}
