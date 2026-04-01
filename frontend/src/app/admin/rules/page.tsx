"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
import {
  getAdminRules,
  getAdminRule,
  updateAdminRule,
  type AdminRule,
} from "@/lib/api";

const SEVERITY_STYLES: Record<string, string> = {
  critical:
    "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
  major:
    "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
  review:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-400",
  info: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
};

const SEVERITY_OPTIONS = ["critical", "major", "review", "info"];

export default function AdminRulesPage() {
  const [rules, setRules] = useState<AdminRule[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editRule, setEditRule] = useState<AdminRule | null>(null);
  const [editYaml, setEditYaml] = useState("");
  const [editSeverity, setEditSeverity] = useState("review");
  const [editConfidence, setEditConfidence] = useState("0.8");
  const [editHumanReview, setEditHumanReview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const fetchRules = useCallback(async (domain?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdminRules(
        domain && domain !== "all" ? domain : undefined,
      );
      setRules(res.rules);
      setDomains(res.domains);
    } catch (err) {
      setError(err instanceof Error ? err.message : "규칙 로딩 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules(selectedDomain);
  }, [selectedDomain, fetchRules]);

  const handleRowClick = async (rule: AdminRule) => {
    try {
      const detail = await getAdminRule(rule.rule_id);
      setEditRule(rule);
      setEditYaml(detail.yaml_source);
      setEditSeverity(rule.severity);
      setEditConfidence(String(rule.confidence));
      setEditHumanReview(rule.human_review_required ?? false);
      setEditOpen(true);
    } catch {
      setEditRule(rule);
      setEditYaml("");
      setEditSeverity(rule.severity);
      setEditConfidence(String(rule.confidence));
      setEditHumanReview(rule.human_review_required ?? false);
      setEditOpen(true);
    }
  };

  const handleSave = async () => {
    if (!editRule) return;
    setSaving(true);
    try {
      await updateAdminRule(editRule.rule_id, {
        severity: editSeverity,
        confidence: parseFloat(editConfidence),
        human_review_required: editHumanReview,
      });
      setEditOpen(false);
      setToast("규칙 수정 완료");
      setTimeout(() => setToast(null), 3000);
      fetchRules(selectedDomain);
    } catch (err) {
      setToast(
        err instanceof Error ? err.message : "수정 실패",
      );
      setTimeout(() => setToast(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
        <LoadingSkeleton variant="card" count={3} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => fetchRules(selectedDomain)}
      />
    );
  }

  const filteredRules =
    selectedDomain === "all"
      ? rules
      : rules.filter((r) => r.domain === selectedDomain);

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">규칙 관리</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {rules.length}개 규칙 · {domains.length}개 도메인
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-sm text-muted-foreground shrink-0">
            도메인
          </Label>
          <Select
            value={selectedDomain}
            onValueChange={(v) => setSelectedDomain(v ?? "all")}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">전체</SelectItem>
              {domains.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Separator />

      {/* Rules table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            규칙 목록 ({filteredRules.length}건)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium">ID</th>
                  <th className="text-left px-4 py-2 font-medium">도메인</th>
                  <th className="text-left px-4 py-2 font-medium">심각도</th>
                  <th className="text-left px-4 py-2 font-medium">제목</th>
                  <th className="text-left px-4 py-2 font-medium">신뢰도</th>
                  <th className="text-left px-4 py-2 font-medium">
                    전문가 검토
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRules.map((rule) => (
                  <tr
                    key={rule.rule_id}
                    className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() => handleRowClick(rule)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRowClick(rule);
                    }}
                    tabIndex={0}
                    role="button"
                  >
                    <td className="px-4 py-3 font-mono text-xs">
                      {rule.rule_id}
                    </td>
                    <td className="px-4 py-3">{rule.domain}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={`border-0 text-xs ${SEVERITY_STYLES[rule.severity] ?? ""}`}
                      >
                        {rule.severity}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">{rule.title}</td>
                    <td className="px-4 py-3 text-center">
                      {(rule.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-center">
                      {rule.human_review_required ? "Y" : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              규칙 편집: {editRule?.rule_id}
            </DialogTitle>
            <DialogDescription>
              {editRule?.title}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Severity */}
            <div className="space-y-1.5">
              <Label>심각도</Label>
              <Select value={editSeverity} onValueChange={(v) => setEditSeverity(v ?? "review")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITY_OPTIONS.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Confidence */}
            <div className="space-y-1.5">
              <Label>신뢰도 (0~1)</Label>
              <Input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={editConfidence}
                onChange={(e) => setEditConfidence(e.target.value)}
              />
            </div>

            {/* Human review */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={editHumanReview}
                onChange={(e) => setEditHumanReview(e.target.checked)}
                className="size-4 accent-teal-600 rounded"
              />
              <span className="text-sm">전문가 검토 필요</span>
            </label>

            {/* YAML source (read-only) */}
            {editYaml && (
              <div className="space-y-1.5">
                <Label>YAML 원문</Label>
                <pre className="bg-muted rounded-lg p-3 text-xs overflow-auto max-h-48 font-mono">
                  {editYaml}
                </pre>
              </div>
            )}

            {/* Legal basis */}
            {editRule?.legal_basis && (
              <div className="space-y-1.5">
                <Label>법적 근거</Label>
                <p className="text-sm text-muted-foreground">
                  {editRule.legal_basis}
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditOpen(false)}
            >
              취소
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "저장 중..." : "저장"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-foreground text-background px-4 py-2.5 text-sm shadow-lg animate-in fade-in slide-in-from-bottom-4">
          {toast}
        </div>
      )}
    </div>
  );
}
