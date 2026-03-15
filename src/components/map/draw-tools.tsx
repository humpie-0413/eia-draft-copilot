"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { Button } from "@/components/ui/button";
import { MousePointer2, Pencil, RotateCcw, Trash2 } from "lucide-react";

interface DrawToolsProps {
  map: maplibregl.Map | null;
  /** 기존 geometry (편집 모드용) */
  initialGeometry?: GeoJSON.Polygon | null;
  /** 그리기 완료 콜백 — GeoJSON Polygon 반환 */
  onDrawComplete: (geometry: GeoJSON.Polygon | null) => void;
}

type DrawMode = "idle" | "drawing" | "editing";

/**
 * 폴리곤 그리기/편집 도구.
 * 클릭으로 꼭짓점을 추가하고, 더블클릭으로 폴리곤을 완성한다.
 */
export function DrawTools({
  map,
  initialGeometry,
  onDrawComplete,
}: DrawToolsProps) {
  const [mode, setMode] = useState<DrawMode>("idle");
  const [vertices, setVertices] = useState<[number, number][]>([]);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  // 클릭 핸들러 참조 (이벤트 해제용)
  const clickHandlerRef = useRef<((e: maplibregl.MapMouseEvent) => void) | null>(null);
  const dblClickHandlerRef = useRef<((e: maplibregl.MapMouseEvent) => void) | null>(null);

  /** 마커 정리 */
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
  }, []);

  /** 그리기 소스/레이어 업데이트 */
  const updateDrawLayer = useCallback(
    (coords: [number, number][]) => {
      if (!map) return;

      const sourceId = "draw-source";
      const lineId = "draw-line";
      const fillId = "draw-fill";

      // 폴리곤 또는 라인 GeoJSON 구성
      let geojsonData: GeoJSON.Feature;
      if (coords.length >= 3) {
        geojsonData = {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [[...coords, coords[0]]],
          },
        };
      } else if (coords.length >= 2) {
        geojsonData = {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: coords,
          },
        };
      } else {
        geojsonData = {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Point",
            coordinates: coords[0] || [0, 0],
          },
        };
      }

      if (map.getSource(sourceId)) {
        (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(geojsonData);
      } else {
        map.addSource(sourceId, { type: "geojson", data: geojsonData });
        map.addLayer({
          id: fillId,
          type: "fill",
          source: sourceId,
          paint: {
            "fill-color": "#f97316",
            "fill-opacity": 0.2,
          },
          filter: ["==", "$type", "Polygon"],
        });
        map.addLayer({
          id: lineId,
          type: "line",
          source: sourceId,
          paint: {
            "line-color": "#f97316",
            "line-width": 2,
            "line-dasharray": [3, 3],
          },
        });
      }

      // 꼭짓점 마커
      clearMarkers();
      coords.forEach((coord, idx) => {
        const el = document.createElement("div");
        el.style.width = "12px";
        el.style.height = "12px";
        el.style.backgroundColor = idx === 0 ? "#f97316" : "#ffffff";
        el.style.border = "2px solid #f97316";
        el.style.borderRadius = "50%";
        el.style.cursor = "pointer";

        const marker = new maplibregl.Marker({ element: el, draggable: mode === "editing" })
          .setLngLat(coord)
          .addTo(map);

        if (mode === "editing") {
          marker.on("dragend", () => {
            const lngLat = marker.getLngLat();
            setVertices((prev) => {
              const next = [...prev];
              next[idx] = [lngLat.lng, lngLat.lat];
              return next;
            });
          });
        }

        markersRef.current.push(marker);
      });
    },
    [map, mode, clearMarkers],
  );

  /** 그리기 레이어 제거 */
  const removeDrawLayer = useCallback(() => {
    if (!map) return;
    ["draw-fill", "draw-line"].forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    if (map.getSource("draw-source")) map.removeSource("draw-source");
    clearMarkers();
  }, [map, clearMarkers]);

  /** 그리기 시작 */
  const startDrawing = useCallback(() => {
    if (!map) return;
    setMode("drawing");
    setVertices([]);
    removeDrawLayer();

    const onClick = (e: maplibregl.MapMouseEvent) => {
      const coord: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      setVertices((prev) => [...prev, coord]);
    };

    const onDblClick = (e: maplibregl.MapMouseEvent) => {
      e.preventDefault();
      // 그리기 완료
      setMode("editing");
      // 이벤트 해제
      if (clickHandlerRef.current) map.off("click", clickHandlerRef.current);
      if (dblClickHandlerRef.current) map.off("dblclick", dblClickHandlerRef.current);
      clickHandlerRef.current = null;
      dblClickHandlerRef.current = null;
    };

    clickHandlerRef.current = onClick;
    dblClickHandlerRef.current = onDblClick;

    map.on("click", onClick);
    map.on("dblclick", onDblClick);
    map.getCanvas().style.cursor = "crosshair";
  }, [map, removeDrawLayer]);

  /** 초기 geometry 로드 */
  useEffect(() => {
    if (!map || !initialGeometry) return;
    const ring = initialGeometry.coordinates[0];
    // 마지막 좌표는 첫 좌표와 같으므로 제거
    const coords = ring.slice(0, -1) as [number, number][];
    setVertices(coords);
    setMode("editing");
  }, [map, initialGeometry]);

  /** vertices 변경 시 레이어 업데이트 + 콜백 */
  useEffect(() => {
    if (!map) return;
    if (vertices.length === 0) return;

    updateDrawLayer(vertices);

    // 3개 이상이면 폴리곤 완성
    if (vertices.length >= 3 && mode === "editing") {
      const polygon: GeoJSON.Polygon = {
        type: "Polygon",
        coordinates: [[...vertices, vertices[0]]],
      };
      onDrawComplete(polygon);
    }
  }, [vertices, map, mode, updateDrawLayer, onDrawComplete]);

  /** 초기화 */
  const handleReset = useCallback(() => {
    setVertices([]);
    setMode("idle");
    removeDrawLayer();
    onDrawComplete(null);

    if (map) {
      if (clickHandlerRef.current) map.off("click", clickHandlerRef.current);
      if (dblClickHandlerRef.current) map.off("dblclick", dblClickHandlerRef.current);
      clickHandlerRef.current = null;
      dblClickHandlerRef.current = null;
      map.getCanvas().style.cursor = "";
    }
  }, [map, removeDrawLayer, onDrawComplete]);

  /** 삭제 */
  const handleDelete = useCallback(() => {
    handleReset();
  }, [handleReset]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (map) {
        if (clickHandlerRef.current) map.off("click", clickHandlerRef.current);
        if (dblClickHandlerRef.current) map.off("dblclick", dblClickHandlerRef.current);
        map.getCanvas().style.cursor = "";
      }
      clearMarkers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 면적 계산 (㎡, 근사) — Shoelace formula with latitude correction */
  const area = vertices.length >= 3 ? calculateAreaM2(vertices) : 0;

  return (
    <div className="space-y-2">
      {/* 도구 버튼 */}
      <div className="flex items-center gap-2">
        <Button
          variant={mode === "drawing" ? "default" : "outline"}
          size="sm"
          onClick={startDrawing}
          disabled={mode === "drawing"}
        >
          <Pencil className="mr-1.5 h-3.5 w-3.5" />
          {mode === "idle" ? "폴리곤 그리기" : mode === "drawing" ? "그리는 중…" : "다시 그리기"}
        </Button>
        {mode === "editing" && (
          <Button variant="outline" size="sm" onClick={() => setMode("editing")}>
            <MousePointer2 className="mr-1.5 h-3.5 w-3.5" />
            꼭짓점 편집
          </Button>
        )}
        {vertices.length > 0 && (
          <>
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              초기화
            </Button>
            <Button variant="outline" size="sm" onClick={handleDelete}>
              <Trash2 className="mr-1.5 h-3.5 w-3.5" />
              삭제
            </Button>
          </>
        )}
      </div>

      {/* 상태 정보 */}
      {mode === "drawing" && (
        <p className="text-xs text-muted-foreground">
          지도를 클릭하여 꼭짓점을 추가하세요. 더블클릭으로 완성합니다. (현재 {vertices.length}개 점)
        </p>
      )}
      {mode === "editing" && vertices.length >= 3 && (
        <div className="text-xs text-muted-foreground space-y-0.5">
          <p>꼭짓점: {vertices.length}개 | 면적: {formatArea(area)}</p>
          <p>
            중심점: [{((vertices.reduce((s, v) => s + v[0], 0) / vertices.length)).toFixed(6)},{" "}
            {((vertices.reduce((s, v) => s + v[1], 0) / vertices.length)).toFixed(6)}]
          </p>
        </div>
      )}
    </div>
  );
}

/** 면적 계산 (㎡) — Shoelace formula + 위도 보정 */
function calculateAreaM2(coords: [number, number][]): number {
  const n = coords.length;
  if (n < 3) return 0;

  // 위도 중심
  const avgLat = coords.reduce((s, c) => s + c[1], 0) / n;
  const latRad = (avgLat * Math.PI) / 180;
  const metersPerDegLng = 111320 * Math.cos(latRad);
  const metersPerDegLat = 110540;

  // Shoelace formula (미터 변환)
  let area = 0;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    const xi = coords[i][0] * metersPerDegLng;
    const yi = coords[i][1] * metersPerDegLat;
    const xj = coords[j][0] * metersPerDegLng;
    const yj = coords[j][1] * metersPerDegLat;
    area += xi * yj - xj * yi;
  }

  return Math.abs(area / 2);
}

/** 면적 포맷 */
function formatArea(m2: number): string {
  if (m2 >= 1_000_000) return `${(m2 / 1_000_000).toFixed(2)} km²`;
  return `${Math.round(m2).toLocaleString()} ㎡`;
}
