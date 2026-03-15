"use client";

import { useCallback } from "react";
import maplibregl from "maplibre-gl";
import { BaseMap } from "./base-map";

interface MiniMapProps {
  /** 프로젝트 geometry (GeoJSON) */
  geometry?: GeoJSON.Geometry | null;
  /** 추가 마커 표시용 포인트들 [lng, lat][] */
  points?: Array<{ lng: number; lat: number; color?: string }>;
  /** CSS 클래스 */
  className?: string;
}

/**
 * 미니 지도 컴포넌트.
 * 프로젝트 상세 페이지, 증거 작업대 등에서 사용.
 */
export function MiniMap({
  geometry,
  points,
  className = "h-[150px] w-[200px]",
}: MiniMapProps) {
  const handleMapReady = useCallback(
    (map: maplibregl.Map) => {
      // 사업 경계 표시
      if (geometry) {
        map.addSource("mini-boundary", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry,
          },
        });
        map.addLayer({
          id: "mini-boundary-fill",
          type: "fill",
          source: "mini-boundary",
          paint: {
            "fill-color": "#16a34a",
            "fill-opacity": 0.15,
          },
        });
        map.addLayer({
          id: "mini-boundary-line",
          type: "line",
          source: "mini-boundary",
          paint: {
            "line-color": "#16a34a",
            "line-width": 2,
          },
        });
      }

      // 추가 포인트 마커
      if (points && points.length > 0) {
        points.forEach((pt, idx) => {
          const el = document.createElement("div");
          el.style.width = "8px";
          el.style.height = "8px";
          el.style.backgroundColor = pt.color || "#2563eb";
          el.style.borderRadius = "50%";
          el.style.border = "1px solid white";

          new maplibregl.Marker({ element: el })
            .setLngLat([pt.lng, pt.lat])
            .addTo(map);
        });
      }

      // 상호작용 비활성화
      map.scrollZoom.disable();
      map.dragPan.disable();
      map.dragRotate.disable();
      map.touchZoomRotate.disable();
      map.doubleClickZoom.disable();
    },
    [geometry, points],
  );

  if (!geometry) {
    return (
      <div
        className={`${className} flex items-center justify-center rounded border bg-gray-50 text-xs text-gray-400`}
      >
        geometry 없음
      </div>
    );
  }

  return (
    <div className={`${className} overflow-hidden rounded border`}>
      <BaseMap
        geometry={geometry}
        onMapReady={handleMapReady}
        minimal
        className="h-full w-full"
      />
    </div>
  );
}
