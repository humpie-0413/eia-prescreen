"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ScreeningMap } from "@/components/map/screening-map";
import { createScreening } from "@/lib/api";
import { toast } from "sonner";
import { validateCoordinates, hasCoordErrors, type CoordError } from "@/lib/validate";
import type { ProjectType, LocationInput } from "@/types/screening";
import {
  Route,
  Building2,
  Factory,
  Zap,
  Ship,
  Droplets,
  TrainFront,
  Plane,
  Waves,
  TreePine,
  Mountain,
  Dumbbell,
  Trash2,
  Shield,
  Pickaxe,
  LandPlot,
  MapPin,
  Plus,
  X,
} from "lucide-react";

/* ── Project type config with icons ── */

const PROJECT_TYPES: {
  value: ProjectType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { value: "urban_dev", label: "도시개발", icon: Building2 },
  { value: "industrial", label: "산업단지", icon: Factory },
  { value: "energy", label: "에너지개발", icon: Zap },
  { value: "port", label: "항만건설", icon: Ship },
  { value: "road", label: "도로건설", icon: Route },
  { value: "water_resource", label: "수자원개발", icon: Droplets },
  { value: "railway", label: "철도건설", icon: TrainFront },
  { value: "airport", label: "공항건설", icon: Plane },
  { value: "river", label: "하천이용·개발", icon: Waves },
  { value: "tourism", label: "관광단지", icon: TreePine },
  { value: "mountain", label: "산지개발", icon: Mountain },
  { value: "sports", label: "체육시설", icon: Dumbbell },
  { value: "waste", label: "폐기물처리", icon: Trash2 },
  { value: "military", label: "국방·군사", icon: Shield },
  { value: "mining", label: "광업", icon: Pickaxe },
  { value: "reclamation", label: "매립·간척", icon: LandPlot },
  { value: "special_area", label: "특정지역", icon: MapPin },
];

/* ── Types ── */

interface SiteEntry {
  id: number;
  name: string;
  address: string;
  location: LocationInput | null;
  projectType: ProjectType;
  projectScale: string;
}

function emptySite(id: number): SiteEntry {
  return { id, name: "", address: "", location: null, projectType: "road", projectScale: "" };
}

/* ── Page ── */

export default function NewScreeningPage() {
  const router = useRouter();
  const [sites, setSites] = useState<SiteEntry[]>([emptySite(1)]);
  const [activeSiteIndex, setActiveSiteIndex] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<1 | 2>(1); // 1: type select, 2: details
  const [coordErrors, setCoordErrors] = useState<CoordError>({});
  const [submitProgress, setSubmitProgress] = useState(0);

  const activeSite = sites[activeSiteIndex];

  function updateSite(index: number, updates: Partial<SiteEntry>) {
    setSites((prev) => prev.map((s, i) => (i === index ? { ...s, ...updates } : s)));
  }

  function addSite() {
    if (sites.length >= 3) return;
    const newSite = emptySite(sites.length + 1);
    setSites((prev) => [...prev, newSite]);
    setActiveSiteIndex(sites.length);
    setStep(1);
  }

  function removeSite(index: number) {
    if (sites.length <= 1) return;
    setSites((prev) => prev.filter((_, i) => i !== index));
    setActiveSiteIndex(Math.max(0, activeSiteIndex - 1));
  }

  function handleLocationSelect(lng: number, lat: number) {
    const errors = validateCoordinates(lat, lng);
    setCoordErrors(errors);
    if (hasCoordErrors(errors)) {
      toast.error("좌표 범위를 확인하세요", {
        description: errors.lat || errors.lng,
      });
      return;
    }
    updateSite(activeSiteIndex, { location: { lng, lat } });
  }

  function handleTypeSelect(type: ProjectType) {
    updateSite(activeSiteIndex, { projectType: type });
    setStep(2);
  }

  async function handleSubmit() {
    setError(null);
    const site = sites[0];
    if (!site.name.trim()) {
      setError("사업명을 입력하세요.");
      return;
    }

    // Validate coordinates if provided
    if (site.location) {
      const errors = validateCoordinates(site.location.lat, site.location.lng);
      if (hasCoordErrors(errors)) {
        setCoordErrors(errors);
        toast.error("좌표 범위를 확인하세요");
        return;
      }
    }

    setIsSubmitting(true);
    setSubmitProgress(0);

    // Animate progress bar during submission
    const progressInterval = setInterval(() => {
      setSubmitProgress((prev) => Math.min(prev + 8, 90));
    }, 100);

    try {
      const result = await createScreening({
        project_name: site.name,
        project_type: site.projectType,
        project_scale: site.projectScale || undefined,
        address: site.address || undefined,
        location: site.location ?? undefined,
      });

      clearInterval(progressInterval);
      setSubmitProgress(100);
      toast.success("스크리닝 생성 완료");
      router.push(`/screening/${result.id}/dashboard`);
    } catch (e) {
      clearInterval(progressInterval);
      setSubmitProgress(0);
      const msg = e instanceof Error ? e.message : "검토 요청에 실패했습니다.";
      setError(msg);
      toast.error("검토 요청 실패", { description: msg });
    } finally {
      setIsSubmitting(false);
    }
  }

  const selectedTypeLabel =
    PROJECT_TYPES.find((t) => t.value === activeSite.projectType)?.label ?? "";

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-6 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">새 사전검토 시작</h1>
        <p className="text-sm text-muted-foreground mt-1">
          사업 위치와 유형을 입력하면 입지 리스크와 우선 검토 항목을 분석합니다.
        </p>
      </div>

      {/* Site tabs (multi-site) */}
      {sites.length > 1 && (
        <div className="flex items-center gap-2">
          {sites.map((site, i) => (
            <button
              key={site.id}
              onClick={() => { setActiveSiteIndex(i); setStep(1); }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                i === activeSiteIndex
                  ? "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200"
                  : "bg-muted text-muted-foreground hover:bg-accent"
              }`}
            >
              부지 {i + 1}
              {sites.length > 1 && (
                <button
                  onClick={(e) => { e.stopPropagation(); removeSite(i); }}
                  className="ml-0.5 hover:text-destructive"
                >
                  <X className="size-3" />
                </button>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Step indicator */}
      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={() => setStep(1)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full transition-colors ${
            step === 1
              ? "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300 font-medium"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className="size-5 rounded-full bg-teal-600 text-white text-xs flex items-center justify-center font-bold">
            1
          </span>
          사업유형
        </button>
        <div className="w-8 h-px bg-border" />
        <button
          onClick={() => {
            if (!activeSite.projectType) {
              toast.warning("사업유형을 선택하세요");
              return;
            }
            setStep(2);
          }}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full transition-colors ${
            step === 2
              ? "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300 font-medium"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <span className={`size-5 rounded-full text-xs flex items-center justify-center font-bold ${
            step >= 2 ? "bg-teal-600 text-white" : "bg-muted text-muted-foreground"
          }`}>
            2
          </span>
          사업정보 + 위치
        </button>
      </div>

      <AnimatePresence mode="wait">
        {/* ── Step 1: Type selection grid ── */}
        {step === 1 && (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-base">사업유형 선택</CardTitle>
                <p className="text-xs text-muted-foreground">
                  환경영향평가법 시행령 별표3 기준 17개 유형
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
                  {PROJECT_TYPES.map((type) => {
                    const Icon = type.icon;
                    const selected = activeSite.projectType === type.value;
                    return (
                      <button
                        key={type.value}
                        onClick={() => handleTypeSelect(type.value)}
                        className={`flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all hover:shadow-md ${
                          selected
                            ? "border-teal-500 bg-teal-50 dark:bg-teal-950/30 text-teal-700 dark:text-teal-300 shadow-sm"
                            : "border-border hover:border-teal-300 dark:hover:border-teal-700"
                        }`}
                      >
                        <Icon className={`size-6 ${selected ? "text-teal-600 dark:text-teal-400" : "text-muted-foreground"}`} />
                        <span className="text-xs font-medium leading-tight">
                          {type.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* ── Step 2: Details + Map ── */}
        {step === 2 && (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Form */}
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-base">사업 정보</CardTitle>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300 font-medium">
                        {selectedTypeLabel}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">사업명 *</Label>
                      <Input
                        id="name"
                        placeholder="예: 양평 국도 우회도로 건설사업"
                        value={activeSite.name}
                        onChange={(e) => updateSite(activeSiteIndex, { name: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="scale">사업규모</Label>
                      <Input
                        id="scale"
                        placeholder="예: L=4.2km, W=20m (4차로)"
                        value={activeSite.projectScale}
                        onChange={(e) => updateSite(activeSiteIndex, { projectScale: e.target.value })}
                      />
                    </div>

                    <Separator />

                    <div className="space-y-2">
                      <Label htmlFor="address">주소 검색</Label>
                      <Input
                        id="address"
                        placeholder="주소를 입력하거나 지도에서 위치를 선택하세요"
                        value={activeSite.address}
                        onChange={(e) => updateSite(activeSiteIndex, { address: e.target.value })}
                      />
                    </div>

                    {/* Manual coordinate inputs */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor="lat" className="text-xs">위도 (Lat)</Label>
                        <Input
                          id="lat"
                          type="number"
                          step="0.0001"
                          placeholder="예: 35.82"
                          value={activeSite.location?.lat ?? ""}
                          onChange={(e) => {
                            const lat = parseFloat(e.target.value);
                            const lng = activeSite.location?.lng ?? 127.0;
                            if (!isNaN(lat)) {
                              handleLocationSelect(lng, lat);
                            }
                          }}
                        />
                        {coordErrors.lat && (
                          <p className="text-xs text-destructive">{coordErrors.lat}</p>
                        )}
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="lng" className="text-xs">경도 (Lng)</Label>
                        <Input
                          id="lng"
                          type="number"
                          step="0.0001"
                          placeholder="예: 126.71"
                          value={activeSite.location?.lng ?? ""}
                          onChange={(e) => {
                            const lng = parseFloat(e.target.value);
                            const lat = activeSite.location?.lat ?? 37.5;
                            if (!isNaN(lng)) {
                              handleLocationSelect(lng, lat);
                            }
                          }}
                        />
                        {coordErrors.lng && (
                          <p className="text-xs text-destructive">{coordErrors.lng}</p>
                        )}
                      </div>
                    </div>
                    {activeSite.location && (
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <MapPin className="size-3" />
                        {activeSite.location.lat.toFixed(5)}, {activeSite.location.lng.toFixed(5)}
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Progress bar */}
                {isSubmitting && (
                  <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
                    <motion.div
                      className="h-full bg-primary rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${submitProgress}%` }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3">
                  <Button
                    className="flex-1 bg-teal-600 hover:bg-teal-700 text-white rounded-lg"
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "분석 중..." : "검토 시작"}
                  </Button>
                  {sites.length < 3 && (
                    <Button variant="outline" onClick={addSite} className="gap-1.5">
                      <Plus className="size-4" />
                      부지 추가
                    </Button>
                  )}
                </div>

                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
              </div>

              {/* Right: Map */}
              <div>
                <ScreeningMap
                  className="h-[500px] lg:h-full lg:min-h-[500px] rounded-xl overflow-hidden border border-border"
                  center={
                    activeSite.location
                      ? [activeSite.location.lng, activeSite.location.lat]
                      : undefined
                  }
                  zoom={activeSite.location ? 14 : undefined}
                  onLocationSelect={handleLocationSelect}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
