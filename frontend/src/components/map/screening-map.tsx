"use client";

import { useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect } from "react";

interface ScreeningMapProps {
  center?: [number, number]; // [lng, lat]
  zoom?: number;
  onLocationSelect?: (lng: number, lat: number) => void;
  className?: string;
  markers?: Array<{ lng: number; lat: number; label?: string }>;
}

const DEFAULT_CENTER: [number, number] = [127.0, 37.5]; // South Korea center
const DEFAULT_ZOOM = 7;
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export function ScreeningMap({
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  onLocationSelect,
  className,
  markers,
}: ScreeningMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center,
      zoom,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );

    map.on("load", () => setIsReady(true));

    if (onLocationSelect) {
      map.on("click", (e) => {
        const { lng, lat } = e.lngLat;

        // Remove existing marker
        if (markerRef.current) {
          markerRef.current.remove();
        }

        // Add new marker
        markerRef.current = new maplibregl.Marker({ color: "#0d9488" })
          .setLngLat([lng, lat])
          .addTo(map);

        onLocationSelect(lng, lat);
      });

      // Change cursor
      map.getCanvas().style.cursor = "crosshair";
    }

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update markers
  useEffect(() => {
    if (!mapRef.current || !isReady || !markers) return;
    // Static markers (additional to click marker)
    for (const m of markers) {
      new maplibregl.Marker({ color: "#0d9488" })
        .setLngLat([m.lng, m.lat])
        .addTo(mapRef.current);
    }
  }, [markers, isReady]);

  return (
    <div
      className={`relative rounded-lg overflow-hidden border border-border ${className ?? ""}`}
      role="application"
      aria-label="리스크 맵"
    >
      <div ref={containerRef} className="w-full h-full min-h-[300px]" role="img" aria-label="지도 영역" />
      {onLocationSelect && (
        <div className="absolute top-2 left-2 bg-card/90 backdrop-blur-sm text-xs px-2 py-1 rounded border border-border text-muted-foreground">
          지도를 클릭하여 위치를 선택하세요
        </div>
      )}
    </div>
  );
}
