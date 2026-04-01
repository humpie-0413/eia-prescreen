"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import { Plus, Columns2, Home, Settings } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "홈", icon: Home },
  { href: "/screening/new", label: "새 검토", icon: Plus },
  { href: "/screening/compare", label: "부지 비교", icon: Columns2 },
];

const ADMIN_ITEMS = [
  { href: "/admin/rules", label: "규칙 관리", icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === href;
  if (href === "/screening/new") return pathname === href;
  return pathname.startsWith(href);
}

function getIsAdmin(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const token = localStorage.getItem("access_token");
    if (!token) return false;
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role === "admin";
  } catch {
    return false;
  }
}

function useIsAdmin(): boolean {
  const [isAdmin] = useState(getIsAdmin);
  return isAdmin;
}

export function Sidebar() {
  const pathname = usePathname();
  const isAdmin = useIsAdmin();

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-56 flex-col border-r border-border bg-sidebar h-screen sticky top-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border">
          <div className="h-7 w-7 rounded-lg bg-teal-600 flex items-center justify-center shadow-sm">
            <span className="text-white text-xs font-bold">E</span>
          </div>
          <div>
            <span className="font-semibold text-sm block leading-tight">EIA Pre-Screen</span>
            <span className="text-[10px] text-muted-foreground leading-none">환경영향평가 사전검토</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                <Icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
          {isAdmin && (
            <>
              <div className="pt-3 pb-1 px-3">
                <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">관리자</span>
              </div>
              {ADMIN_ITEMS.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      active
                        ? "bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    <Icon className="size-4" />
                    {item.label}
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* Footer */}
        <div className="px-3 pt-3 pb-2 border-t border-border space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground font-mono">v1.0.0</span>
            <ThemeToggle />
          </div>
          <p className="text-[10px] text-muted-foreground leading-tight">
            법적 판정 시스템이 아닙니다.
            <br />
            전문가 검토 및 현장조사가 필요합니다.
          </p>
        </div>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-card/95 backdrop-blur-sm border-t border-border flex items-center justify-around h-14">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1.5 text-xs transition-colors ${
                active
                  ? "text-teal-700 dark:text-teal-300"
                  : "text-muted-foreground"
              }`}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
        <ThemeToggle />
      </nav>
    </>
  );
}
