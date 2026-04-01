"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "./risk-badge";
import type { RiskCard } from "@/types/screening";

interface EvidenceDrawerProps {
  card: RiskCard | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EvidenceDrawer({ card, open, onOpenChange }: EvidenceDrawerProps) {
  if (!card) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <RiskBadge severity={card.severity} />
            <span className="text-xs text-muted-foreground">{card.rule_id}</span>
          </div>
          <SheetTitle className="text-base">{card.title}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          {/* Rationale */}
          <section>
            <h4 className="text-sm font-medium mb-1.5">판정 근거</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {card.rationale}
            </p>
          </section>

          <Separator />

          {/* Evidence */}
          {card.evidence && (
            <section>
              <h4 className="text-sm font-medium mb-1.5">근거 데이터</h4>
              <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
                {JSON.stringify(card.evidence, null, 2)}
              </pre>
            </section>
          )}

          <Separator />

          {/* Next Action */}
          {card.next_action && (
            <section>
              <h4 className="text-sm font-medium mb-1.5">후속 조치</h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {card.next_action}
              </p>
            </section>
          )}

          {/* Legal Basis */}
          {card.legal_basis && (
            <section>
              <h4 className="text-sm font-medium mb-1.5">관련 법령</h4>
              <p className="text-sm text-muted-foreground">{card.legal_basis}</p>
            </section>
          )}

          {/* Meta */}
          <Separator />
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {card.confidence != null && (
              <span>신뢰도: {(card.confidence * 100).toFixed(0)}%</span>
            )}
            {card.human_review_required && (
              <span className="text-orange-600 dark:text-orange-400">
                전문가 검토 필요
              </span>
            )}
            {card.trigger_dataset && (
              <span>데이터: {card.trigger_dataset}</span>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
