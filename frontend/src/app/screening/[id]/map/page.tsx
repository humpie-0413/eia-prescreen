"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/risk/risk-badge";
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
import { evaluateScreening, getScreening } from "@/lib/api";
import type { Severity } from "@/types/screening";
import { SEVERITY_CONFIG } from "@/types/screening";
import { Layers, ChevronLeft, ChevronRight } from "lucide-react";

const RADIUS_CIRCLES = [
  { radius: 1000, label: "1km", color: "rgba(20,184,166,0.12)", stroke: "rgba(20,184,166,0.5)" },
  { radius: 3000, label: "3km", color: "rgba(20,184,166,0.06)", stroke: "rgba(20,184,166,0.3)" },
  { radius: 5000, label: "5km", color: "rgba(20,184,166,0.03)", stroke: "rgba(20,184,166,0.2)" },
];

const SEVERITY_MARKER_COLORS: Record<string, string> = {
  critical: "#EF4444",
  major: "#F97316",
  review: "#3B82F6",
  info: "#6B7280",
};

interface RiskPoint {
  id: string;
  rule_id: string;
  title: string;
  severity: Severity;
  rationale: string;
  legal_basis?: string;
  lng: number;
  lat: number;
}

function createCircleGeoJSON(
  center: [number, number],
  radiusM: number,
  steps = 64,
): GeoJSON.Feature<GeoJSON.Polygon> {
  const coords: [number, number][] = [];
  const lat = center[1];
  const lng = center[0];
  for (let i = 0; i <= steps; i++) {
    const angle = (i / steps) * 2 * Math.PI;
    const dLat = (radiusM / 111320) * Math.cos(angle);
    const dLng =
      (radiusM / (111320 * Math.cos((lat * Math.PI) / 180))) * Math.sin(angle);
    coords.push([lng + dLng, lat + dLat]);
  }
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [coords] },
  };
}

export default function RiskMapPage() {
  const { id } = useParams<{ id: string }>();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskPoints, setRiskPoints] = useState<RiskPoint[]>([]);
  const [center, setCenter] = useState<[number, number]>([127.0, 37.5]);
  const [panelOpen, setPanelOpen] = useState(true);
  const [layers, setLayers] = useState({
    radius: true,
    riskPoints: true,
  });

  // Fetch screening + evaluation data
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [screening, evaluation] = await Promise.all([
          getScreening(id, { signal: controller.signal }),
          evaluateScreening(id, { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;

        const lng = screening.lng ?? 127.0;
        const lat = screening.lat ?? 37.5;
        setCenter([lng, lat]);

        // Generate risk points with slight random offsets around center
        const points: RiskPoint[] = evaluation.risk_cards.map((card, idx) => {
          const angle = (idx / Math.max(evaluation.risk_cards.length, 1)) * 2 * Math.PI;
          const dist = 0.005 + Math.random() * 0.01;
          return {
            id: String(idx),
            rule_id: card.rule_id,
            title: card.title,
            severity: card.severity as Severity,
            rationale: card.rationale,
            legal_basis: card.legal_basis ?? undefined,
            lng: lng + dist * Math.cos(angle),
            lat: lat + dist * Math.sin(angle),
          };
        });
        setRiskPoints(points);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "데이터 로딩 실패");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [id]);

  // Initialize map
  const initMap = useCallback(async () => {
    if (!mapContainerRef.current || loading || error) return;

    const maplibregl = (await import("maplibre-gl")).default;
    await import("maplibre-gl/dist/maplibre-gl.css");

    if (mapRef.current) {
      mapRef.current.remove();
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          carto: {
            type: "raster",
            tiles: [
              "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
            attribution: "&copy; CARTO, &copy; OpenStreetMap",
          },
        },
        layers: [
          {
            id: "carto-tiles",
            type: "raster",
            source: "carto",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: center,
      zoom: 12,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 150 }),
      "bottom-right",
    );

    map.on("load", () => {
      // Add radius circles
      RADIUS_CIRCLES.forEach((circle, idx) => {
        const sourceId = `radius-${idx}`;
        map.addSource(sourceId, {
          type: "geojson",
          data: createCircleGeoJSON(center, circle.radius),
        });
        map.addLayer({
          id: `${sourceId}-fill`,
          type: "fill",
          source: sourceId,
          paint: {
            "fill-color": circle.color,
          },
        });
        map.addLayer({
          id: `${sourceId}-line`,
          type: "line",
          source: sourceId,
          paint: {
            "line-color": circle.stroke,
            "line-width": 1.5,
            "line-dasharray": [4, 3],
          },
        });
      });

      // Site marker
      new maplibregl.Marker({ color: "#DC2626" })
        .setLngLat(center)
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(
            '<div style="font-family:sans-serif;font-size:13px;font-weight:600;">사업 위치</div>',
          ),
        )
        .addTo(map);

      // Risk point markers
      for (const pt of riskPoints) {
        const color = SEVERITY_MARKER_COLORS[pt.severity] ?? "#6B7280";
        const el = document.createElement("div");
        el.style.width = "14px";
        el.style.height = "14px";
        el.style.borderRadius = "50%";
        el.style.backgroundColor = color;
        el.style.border = "2px solid white";
        el.style.boxShadow = "0 1px 3px rgba(0,0,0,0.3)";
        el.style.cursor = "pointer";

        new maplibregl.Marker({ element: el })
          .setLngLat([pt.lng, pt.lat])
          .setPopup(
            new maplibregl.Popup({ offset: 12, maxWidth: "280px" }).setHTML(
              `<div style="font-family:sans-serif;">` +
                `<div style="font-size:11px;color:${color};font-weight:700;text-transform:uppercase;margin-bottom:2px;">${pt.severity} · ${pt.rule_id}</div>` +
                `<div style="font-size:13px;font-weight:600;margin-bottom:4px;">${pt.title}</div>` +
                `<div style="font-size:11px;color:#666;line-height:1.4;">${pt.rationale.slice(0, 120)}${pt.rationale.length > 120 ? "…" : ""}</div>` +
                (pt.legal_basis
                  ? `<div style="font-size:10px;color:#999;margin-top:4px;">${pt.legal_basis}</div>`
                  : "") +
                `</div>`,
            ),
          )
          .addTo(map);
      }
    });

    mapRef.current = map;
  }, [center, riskPoints, loading, error]);

  useEffect(() => {
    initMap();
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [initMap]);

  // Toggle layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    RADIUS_CIRCLES.forEach((_, idx) => {
      const vis = layers.radius ? "visible" : "none";
      const fillId = `radius-${idx}-fill`;
      const lineId = `radius-${idx}-line`;
      if (map.getLayer(fillId)) map.setLayoutProperty(fillId, "visibility", vis);
      if (map.getLayer(lineId)) map.setLayoutProperty(lineId, "visibility", vis);
    });
  }, [layers.radius]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <LoadingSkeleton variant="chart" />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  const severityCounts: Record<Severity, number> = { critical: 0, major: 0, review: 0, info: 0 };
  for (const pt of riskPoints) severityCounts[pt.severity]++;

  return (
    <div className="h-[calc(100vh-3.5rem)] flex relative">
      {/* Side panel */}
      <div
        className={`absolute top-0 left-0 z-10 h-full transition-transform duration-300 ${
          panelOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="w-72 h-full bg-card/95 backdrop-blur-sm border-r border-border overflow-y-auto p-3 space-y-3">
          {/* Layer toggles */}
          <Card>
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-xs font-semibold flex items-center gap-1.5">
                <Layers className="size-3.5" />
                레이어
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 space-y-2">
              <label className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={layers.radius}
                  onChange={(e) =>
                    setLayers((l) => ({ ...l, radius: e.target.checked }))
                  }
                  className="size-3.5 accent-teal-600"
                />
                영향 반경 (1/3/5km)
              </label>
              <label className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={layers.riskPoints}
                  onChange={(e) =>
                    setLayers((l) => ({
                      ...l,
                      riskPoints: e.target.checked,
                    }))
                  }
                  className="size-3.5 accent-teal-600"
                />
                리스크 포인트
              </label>
            </CardContent>
          </Card>

          {/* Legend */}
          <Card>
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-xs font-semibold">범례</CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 space-y-1.5">
              <div className="flex items-center gap-2 text-xs">
                <span className="inline-block size-3 rounded-full bg-red-600 border border-white shadow-sm" />
                사업 위치
              </div>
              {(["critical", "major", "review", "info"] as Severity[]).map((sev) => (
                <div key={sev} className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block size-2.5 rounded-full border border-white shadow-sm"
                    style={{ backgroundColor: SEVERITY_MARKER_COLORS[sev] }}
                  />
                  {SEVERITY_CONFIG[sev].label} ({severityCounts[sev]})
                </div>
              ))}
              {RADIUS_CIRCLES.map((c) => (
                <div key={c.label} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="inline-block w-4 h-0 border-t-2 border-dashed border-teal-500" />
                  {c.label} 반경
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Risk list */}
          <Card>
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-xs font-semibold">
                리스크 ({riskPoints.length}건)
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 space-y-1.5 max-h-[40vh] overflow-y-auto">
              {riskPoints.map((pt) => (
                <button
                  key={pt.id}
                  type="button"
                  className="w-full text-left rounded-md border border-border p-2 hover:bg-muted/50 transition-colors"
                  onClick={() => {
                    mapRef.current?.flyTo({
                      center: [pt.lng, pt.lat],
                      zoom: 14,
                    });
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    <RiskBadge severity={pt.severity} />
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {pt.rule_id}
                    </span>
                  </div>
                  <p className="text-xs font-medium mt-1 leading-snug">
                    {pt.title}
                  </p>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Panel toggle button */}
      <Button
        variant="outline"
        size="icon-sm"
        className={`absolute top-3 z-20 transition-all duration-300 ${
          panelOpen ? "left-[18.5rem]" : "left-3"
        } bg-card/90 backdrop-blur-sm`}
        onClick={() => setPanelOpen(!panelOpen)}
      >
        {panelOpen ? (
          <ChevronLeft className="size-4" />
        ) : (
          <ChevronRight className="size-4" />
        )}
      </Button>

      {/* Info badge */}
      <Badge
        variant="outline"
        className="absolute top-3 right-14 z-10 border-0 bg-card/90 backdrop-blur-sm text-xs"
      >
        {riskPoints.length}건 리스크 · {center[1].toFixed(4)}, {center[0].toFixed(4)}
      </Badge>

      {/* Map container */}
      <div ref={mapContainerRef} className="flex-1 h-full" />
    </div>
  );
}
