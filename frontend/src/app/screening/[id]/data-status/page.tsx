"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
import { getScreeningDataStatus } from "@/lib/api";
import type {
  ConnectorStatus,
  ScreeningDataStatusResponse,
} from "@/types/screening";

const STATUS_STYLE: Record<string, string> = {
  stable: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
  unstable:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
  unavailable: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
  unknown: "bg-muted text-muted-foreground",
};

const TIER_STYLE: Record<string, string> = {
  A: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
  B: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400",
  C: "bg-muted text-muted-foreground",
};

const FRESHNESS_STYLE: Record<string, string> = {
  live: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400",
  demo: "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400",
  cached:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
  stale: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
  unknown: "bg-muted text-muted-foreground",
};

const FRESHNESS_LABEL: Record<string, string> = {
  live: "실시간",
  demo: "데모",
  cached: "캐시",
  stale: "오래됨",
  unknown: "알 수 없음",
};

function ConnectorCard({ conn }: { conn: ConnectorStatus }) {
  const freshness = conn.freshness?.freshness ?? "unknown";
  const lastSuccess =
    conn.freshness?.fetched_at ?? conn.freshness?.snapshot_at ?? null;

  return (
    <Card>
      <CardContent className="py-4 px-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <Badge
            variant="outline"
            className={`border-0 text-xs shrink-0 ${TIER_STYLE[conn.tier] ?? TIER_STYLE.C}`}
          >
            {conn.tier}계층
          </Badge>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{conn.description}</p>
            <p className="text-xs text-muted-foreground">{conn.name}</p>
            {lastSuccess && (
              <p className="text-xs text-muted-foreground mt-0.5">
                최종 성공: {new Date(lastSuccess).toLocaleString("ko-KR")}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge
            variant="outline"
            className={`border-0 text-xs ${FRESHNESS_STYLE[freshness]}`}
          >
            {FRESHNESS_LABEL[freshness] ?? freshness}
          </Badge>
          <Badge
            variant="outline"
            className={`border-0 text-xs ${STATUS_STYLE[conn.status] ?? STATUS_STYLE.unknown}`}
          >
            {conn.status}
          </Badge>
          {conn.has_data ? (
            <span className="text-green-600 dark:text-green-400 text-sm font-bold">
              O
            </span>
          ) : (
            <span className="text-red-500 dark:text-red-400 text-sm font-bold">
              X
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CoverageSummary({
  data,
}: {
  data: ScreeningDataStatusResponse;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card>
        <CardContent className="py-3 px-4 text-center">
          <p className="text-2xl font-bold text-teal-600 dark:text-teal-400">
            {data.coverage_pct}%
          </p>
          <p className="text-xs text-muted-foreground">데이터 커버리지</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-3 px-4 text-center">
          <p className="text-2xl font-bold">
            {data.available}/{data.total}
          </p>
          <p className="text-xs text-muted-foreground">가용 커넥터</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-3 px-4 text-center">
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">
            {data.freshness_summary["live"] ?? data.freshness_summary["demo"] ?? 0}
          </p>
          <p className="text-xs text-muted-foreground">실시간/데모</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-3 px-4 text-center">
          <p className="text-2xl font-bold text-orange-500">
            {(data.freshness_summary["stale"] ?? 0) +
              (data.freshness_summary["unknown"] ?? 0)}
          </p>
          <p className="text-xs text-muted-foreground">오래됨/없음</p>
        </CardContent>
      </Card>
    </div>
  );
}

function FreshnessBar({
  summary,
  total,
}: {
  summary: Record<string, number>;
  total: number;
}) {
  if (total === 0) return null;

  const segments = [
    { key: "live", label: "실시간", color: "bg-green-500" },
    { key: "demo", label: "데모", color: "bg-teal-500" },
    { key: "cached", label: "캐시", color: "bg-yellow-500" },
    { key: "stale", label: "오래됨", color: "bg-orange-500" },
    { key: "unknown", label: "없음", color: "bg-gray-400" },
  ];

  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden">
        {segments.map((seg) => {
          const count = summary[seg.key] ?? 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={seg.key}
              className={seg.color}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${count}개`}
            />
          );
        })}
      </div>
      <div className="flex gap-3 mt-2 flex-wrap">
        {segments.map((seg) => {
          const count = summary[seg.key] ?? 0;
          if (count === 0) return null;
          return (
            <div key={seg.key} className="flex items-center gap-1 text-xs text-muted-foreground">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${seg.color}`} />
              {seg.label} ({count})
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DataStatusPage() {
  const { id } = useParams<{ id: string }>();

  const [data, setData] = useState<ScreeningDataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getScreeningDataStatus(id)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.");
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <LoadingSkeleton variant="list" count={6} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState
        message={error ?? "데이터를 불러올 수 없습니다."}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="max-w-4xl mx-auto p-4 md:p-8 space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold">데이터 현황</h1>
        <p className="text-sm text-muted-foreground mt-1">
          스크리닝 ID: {id}
          {data.demo_mode && (
            <Badge variant="outline" className="ml-2 border-0 text-xs bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400">
              데모
            </Badge>
          )}
        </p>
      </div>

      <CoverageSummary data={data} />

      <div>
        <h2 className="text-sm font-semibold mb-2">데이터 신선도</h2>
        <FreshnessBar summary={data.freshness_summary} total={data.total} />
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">커넥터 상태</h2>
        {data.connectors.map((conn) => (
          <ConnectorCard key={conn.name} conn={conn} />
        ))}
      </div>

      {data.connectors.some(
        (c) =>
          !c.has_data ||
          c.freshness?.freshness === "stale" ||
          c.freshness?.freshness === "unknown",
      ) && (
        <Card className="border-orange-200 dark:border-orange-800">
          <CardContent className="py-3 px-5">
            <p className="text-sm font-medium text-orange-700 dark:text-orange-400">
              추가 조사 필요
            </p>
            <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
              {data.connectors
                .filter(
                  (c) =>
                    !c.has_data ||
                    c.freshness?.freshness === "stale" ||
                    c.freshness?.freshness === "unknown",
                )
                .map((c) => (
                  <li key={c.name}>
                    - {c.description} ({c.name}): {c.has_data ? "데이터 오래됨" : "데이터 없음"}
                  </li>
                ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        * {data.demo_mode
          ? "데모 모드에서는 mock 데이터를 사용합니다."
          : "실시간 API 연동 상태입니다."}{" "}
        데이터 기준일자를 반드시 확인하세요.
      </p>
    </motion.div>
  );
}
