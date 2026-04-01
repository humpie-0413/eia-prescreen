interface FallbackBannerProps {
  connectorName: string;
  snapshotAt?: string | null;
}

export function FallbackBanner({ connectorName, snapshotAt }: FallbackBannerProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-yellow-50 border border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800 text-sm">
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-yellow-600 dark:text-yellow-400 shrink-0"
      >
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </svg>
      <span className="text-yellow-800 dark:text-yellow-300">
        <strong>{connectorName}</strong> 실시간 조회에 실패하여 캐시 데이터로 전환되었습니다.
        {snapshotAt && (
          <span className="text-yellow-600 dark:text-yellow-400">
            {" "}(기준: {new Date(snapshotAt).toLocaleString("ko-KR")})
          </span>
        )}
      </span>
    </div>
  );
}
