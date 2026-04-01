"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { LayoutDashboard, Map, Database, BookOpen, FileText, Search } from "lucide-react";

const TABS = [
  { key: "dashboard",   label: "대시보드",    icon: LayoutDashboard, href: (id: string) => `/screening/${id}/dashboard` },
  { key: "map",         label: "리스크 맵",   icon: Map,             href: (id: string) => `/screening/${id}/map` },
  { key: "data-status", label: "데이터 현황", icon: Database,        href: (id: string) => `/screening/${id}/data-status` },
  { key: "cases",       label: "유사사례",    icon: BookOpen,        href: (id: string) => `/screening/${id}/cases` },
  { key: "draft",       label: "초안 생성",   icon: FileText,        href: (id: string) => `/screening/${id}/draft` },
  { key: "rag",         label: "원문 검색",   icon: Search,          href: (id: string) => `/screening/${id}/rag` },
];

export default function ScreeningLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const id = params?.id ?? "";

  return (
    <div className="flex flex-col min-h-screen">
      {/* Tab nav */}
      <div className="sticky top-0 z-30 bg-background/95 backdrop-blur-sm border-b border-border">
        <div className="flex items-center gap-0 overflow-x-auto px-4 md:px-6">
          {TABS.map((tab) => {
            const href = tab.href(id);
            const active = pathname === href;
            const Icon = tab.icon;
            return (
              <Link
                key={tab.key}
                href={href}
                className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? "border-teal-600 text-teal-700 dark:text-teal-400 dark:border-teal-400"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                }`}
              >
                <Icon className="size-4" />
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Page content */}
      <div className="flex-1">{children}</div>

      {/* Disclaimer footer */}
      <footer className="border-t border-border bg-muted/30 px-4 md:px-6 py-3 mt-auto">
        <p className="text-xs text-muted-foreground text-center leading-relaxed">
          이 도구는 법적 판정 시스템이 아닙니다. 데이터 기준일자를 반드시 확인하세요.
          최종 판단은 전문가 현장조사와 법적 검토를 통해 이루어져야 합니다.
        </p>
      </footer>
    </div>
  );
}
