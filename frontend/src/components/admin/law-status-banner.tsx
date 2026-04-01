"use client";

import { useState, useEffect } from "react";
import { TriangleAlert } from "lucide-react";
import { getLawStatus } from "@/lib/api";

export function LawStatusBanner() {
  const [hasOutdated, setHasOutdated] = useState(false);
  const [outdatedNames, setOutdatedNames] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    getLawStatus()
      .then((res) => {
        if (cancelled) return;
        setHasOutdated(res.has_outdated);
        if (res.has_outdated) {
          setOutdatedNames(
            res.laws.filter((l) => l.is_outdated).map((l) => l.law_name),
          );
        }
      })
      .catch(() => {
        // 법령 상태 조회 실패 시 배너 미표시
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!hasOutdated) return null;

  return (
    <div className="rounded-lg border border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-950/50 px-4 py-3 flex items-start gap-3">
      <TriangleAlert className="size-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
      <div className="min-w-0">
        <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
          관련 법령이 개정되었습니다. 관리자 확인이 필요합니다.
        </p>
        <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">
          {outdatedNames.join(", ")}
        </p>
      </div>
    </div>
  );
}
