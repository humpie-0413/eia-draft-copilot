"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { OverlayItem, BufferResponse } from "@/lib/spatial-api";

/** 레이어 정의 */
export interface LayerDef {
  id: string;
  label: string;
  color: string;
  /** 항상 표시 여부 (사업경계) */
  alwaysOn?: boolean;
  visible: boolean;
}

/** 기본 레이어 목록 */
export const DEFAULT_LAYERS: LayerDef[] = [
  { id: "boundary", label: "사업경계", color: "#16a34a", alwaysOn: true, visible: true },
  { id: "buffer-1km", label: "1km 버퍼", color: "#2563eb", visible: true },
  { id: "buffer-5km", label: "5km 버퍼", color: "#7c3aed", visible: true },
  { id: "station-air", label: "대기측정소", color: "#dc2626", visible: true },
  { id: "station-water", label: "수질측정소", color: "#2563eb", visible: true },
  { id: "station-noise", label: "소음측정소", color: "#ca8a04", visible: true },
  { id: "cultural-heritage", label: "문화재", color: "#dc2626", visible: true },
  { id: "land-use", label: "용도지역", color: "#059669", visible: false },
];

/** 용도지역 색상 매핑 */
const LAND_USE_COLORS: Record<string, string> = {
  주거: "#fbbf24",
  상업: "#ef4444",
  공업: "#7c3aed",
  녹지: "#22c55e",
  관리: "#6b7280",
  농림: "#84cc16",
  자연환경보전: "#14b8a6",
};

function getLandUseColor(zoneName: string): string {
  for (const [key, color] of Object.entries(LAND_USE_COLORS)) {
    if (zoneName.includes(key)) return color;
  }
  return "#6b7280";
}

export interface UseMapLayersOptions {
  map: maplibregl.Map | null;
  geometry?: GeoJSON.Geometry | null;
  buffer1km?: BufferResponse | null;
  buffer5km?: BufferResponse | null;
  overlayItems?: OverlayItem[];
}

/**
 * 지도 레이어를 관리하는 훅.
 * 사업경계, 버퍼, 측정소, 문화재, 용도지역 레이어를 추가/제거한다.
 */
export function useMapLayers({
  map,
  geometry,
  buffer1km,
  buffer5km,
  overlayItems = [],
}: UseMapLayersOptions) {
  const [layers, setLayers] = useState<LayerDef[]>(DEFAULT_LAYERS);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  /** 레이어 가시성 토글 */
  const toggleLayer = useCallback(
    (layerId: string) => {
      setLayers((prev) =>
        prev.map((l) =>
          l.id === layerId && !l.alwaysOn
            ? { ...l, visible: !l.visible }
            : l,
        ),
      );
    },
    [],
  );

  // ── 사업경계 레이어 ──
  useEffect(() => {
    if (!map || !geometry) return;
    const sourceId = "boundary-source";
    const fillId = "boundary-fill";
    const lineId = "boundary-line";

    const geojsonData: GeoJSON.Feature = {
      type: "Feature",
      properties: {},
      geometry,
    };

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(geojsonData);
    } else {
      map.addSource(sourceId, { type: "geojson", data: geojsonData });
      map.addLayer({
        id: fillId,
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": "#16a34a",
          "fill-opacity": 0.15,
        },
      });
      map.addLayer({
        id: lineId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#16a34a",
          "line-width": 2,
        },
      });
    }

    return () => {
      if (map.getLayer(fillId)) map.removeLayer(fillId);
      if (map.getLayer(lineId)) map.removeLayer(lineId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    };
  }, [map, geometry]);

  // ── 1km 버퍼 레이어 ──
  useEffect(() => {
    if (!map || !buffer1km) return;
    const sourceId = "buffer-1km-source";
    const lineId = "buffer-1km-line";
    const layerDef = layers.find((l) => l.id === "buffer-1km");

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(
        buffer1km.buffer_geojson as GeoJSON.GeoJSON,
      );
    } else {
      map.addSource(sourceId, {
        type: "geojson",
        data: buffer1km.buffer_geojson as GeoJSON.GeoJSON,
      });
      map.addLayer({
        id: lineId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#2563eb",
          "line-width": 2,
          "line-dasharray": [4, 4],
        },
      });
    }

    const visibility = layerDef?.visible ? "visible" : "none";
    if (map.getLayer(lineId)) {
      map.setLayoutProperty(lineId, "visibility", visibility);
    }

    return () => {
      if (map.getLayer(lineId)) map.removeLayer(lineId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    };
  }, [map, buffer1km, layers]);

  // ── 5km 버퍼 레이어 ──
  useEffect(() => {
    if (!map || !buffer5km) return;
    const sourceId = "buffer-5km-source";
    const lineId = "buffer-5km-line";
    const layerDef = layers.find((l) => l.id === "buffer-5km");

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(
        buffer5km.buffer_geojson as GeoJSON.GeoJSON,
      );
    } else {
      map.addSource(sourceId, {
        type: "geojson",
        data: buffer5km.buffer_geojson as GeoJSON.GeoJSON,
      });
      map.addLayer({
        id: lineId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#7c3aed",
          "line-width": 2,
          "line-dasharray": [6, 4],
        },
      });
    }

    const visibility = layerDef?.visible ? "visible" : "none";
    if (map.getLayer(lineId)) {
      map.setLayoutProperty(lineId, "visibility", visibility);
    }

    return () => {
      if (map.getLayer(lineId)) map.removeLayer(lineId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    };
  }, [map, buffer5km, layers]);

  // ── 측정소 + 문화재 + 용도지역 레이어 ──
  useEffect(() => {
    if (!map || overlayItems.length === 0) return;

    const addedSources: string[] = [];
    const addedLayers: string[] = [];

    // 측정소 분류
    const airStations = overlayItems.filter(
      (i) => i.category === "air_quality" || i.item_type === "대기측정소",
    );
    const waterStations = overlayItems.filter(
      (i) => i.category === "water_quality" || i.item_type === "수질측정소",
    );
    const noiseStations = overlayItems.filter(
      (i) => i.category === "noise_vibration" || i.item_type === "소음측정소",
    );
    const culturalItems = overlayItems.filter(
      (i) => i.category === "cultural_heritage" || i.item_type === "문화재",
    );
    const landUseItems = overlayItems.filter(
      (i) => i.category === "land_use" || i.item_type === "용도지역",
    );

    // 마커 레이어 추가 함수
    function addMarkerLayer(
      layerId: string,
      items: OverlayItem[],
      color: string,
      shape: "circle" | "triangle" | "square",
    ) {
      if (items.length === 0) return;
      const sourceId = `${layerId}-source`;

      const features: GeoJSON.Feature[] = items.map((item) => ({
        type: "Feature",
        properties: {
          name: item.name,
          distance_m: Math.round(item.distance_m),
          item_type: item.item_type,
          category: item.category,
          metadata: JSON.stringify(item.metadata),
        },
        geometry: {
          type: "Point",
          coordinates: [item.lon, item.lat],
        },
      }));

      const geojsonData: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features,
      };

      if (!map!.getSource(sourceId)) {
        map!.addSource(sourceId, { type: "geojson", data: geojsonData });

        if (shape === "circle") {
          map!.addLayer({
            id: layerId,
            type: "circle",
            source: sourceId,
            paint: {
              "circle-radius": 7,
              "circle-color": color,
              "circle-stroke-width": 2,
              "circle-stroke-color": "#ffffff",
            },
          });
        } else {
          // 삼각형/사각형은 symbol 레이어로 표현
          map!.addLayer({
            id: layerId,
            type: "circle",
            source: sourceId,
            paint: {
              "circle-radius": shape === "triangle" ? 8 : 7,
              "circle-color": color,
              "circle-stroke-width": 2,
              "circle-stroke-color": "#ffffff",
            },
          });
        }

        // 라벨 레이어
        const labelId = `${layerId}-label`;
        map!.addLayer({
          id: labelId,
          type: "symbol",
          source: sourceId,
          layout: {
            "text-field": ["get", "name"],
            "text-size": 11,
            "text-offset": [0, 1.5],
            "text-anchor": "top",
            "text-max-width": 10,
          },
          paint: {
            "text-color": "#374151",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.5,
          },
        });

        addedLayers.push(layerId, labelId);
        addedSources.push(sourceId);

        // 클릭 팝업
        map!.on("click", layerId, (e) => {
          if (!e.features || e.features.length === 0) return;
          const feature = e.features[0];
          const props = feature.properties;
          const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

          // 메타데이터 파싱
          let metadataHtml = "";
          try {
            const meta = JSON.parse(props?.metadata || "{}");
            for (const [k, v] of Object.entries(meta)) {
              if (v) metadataHtml += `<div class="text-xs text-gray-500">${k}: ${v}</div>`;
            }
          } catch {
            // 무시
          }

          const html = `
            <div class="p-1">
              <div class="font-semibold text-sm">${props?.name || ""}</div>
              <div class="text-xs text-gray-600">${props?.item_type || ""}</div>
              <div class="text-xs text-blue-600">이격거리: ${props?.distance_m || 0}m</div>
              ${metadataHtml}
            </div>
          `;

          popupRef.current?.remove();
          popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: "240px" })
            .setLngLat(coords)
            .setHTML(html)
            .addTo(map!);
        });

        // 커서 변경
        map!.on("mouseenter", layerId, () => {
          map!.getCanvas().style.cursor = "pointer";
        });
        map!.on("mouseleave", layerId, () => {
          map!.getCanvas().style.cursor = "";
        });
      }
    }

    addMarkerLayer("station-air", airStations, "#dc2626", "triangle");
    addMarkerLayer("station-water", waterStations, "#2563eb", "circle");
    addMarkerLayer("station-noise", noiseStations, "#ca8a04", "square");
    addMarkerLayer("cultural-heritage", culturalItems, "#dc2626", "circle");

    // 용도지역 레이어 (포인트 기반 — 면 데이터가 아닌 증거 좌표)
    if (landUseItems.length > 0) {
      const sourceId = "land-use-source";
      const features: GeoJSON.Feature[] = landUseItems.map((item) => ({
        type: "Feature",
        properties: {
          name: item.name,
          color: getLandUseColor(item.name),
          item_type: item.item_type,
          distance_m: Math.round(item.distance_m),
        },
        geometry: {
          type: "Point",
          coordinates: [item.lon, item.lat],
        },
      }));

      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: "geojson",
          data: { type: "FeatureCollection", features },
        });

        map.addLayer({
          id: "land-use",
          type: "circle",
          source: sourceId,
          paint: {
            "circle-radius": 9,
            "circle-color": ["get", "color"],
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
            "circle-opacity": 0.7,
          },
        });

        const labelId = "land-use-label";
        map.addLayer({
          id: labelId,
          type: "symbol",
          source: sourceId,
          layout: {
            "text-field": ["get", "name"],
            "text-size": 10,
            "text-offset": [0, 1.5],
            "text-anchor": "top",
          },
          paint: {
            "text-color": "#374151",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1,
          },
        });

        addedLayers.push("land-use", labelId);
        addedSources.push(sourceId);
      }
    }

    // 가시성 업데이트
    const layerMappings = [
      { defId: "station-air", mapLayers: ["station-air", "station-air-label"] },
      { defId: "station-water", mapLayers: ["station-water", "station-water-label"] },
      { defId: "station-noise", mapLayers: ["station-noise", "station-noise-label"] },
      { defId: "cultural-heritage", mapLayers: ["cultural-heritage", "cultural-heritage-label"] },
      { defId: "land-use", mapLayers: ["land-use", "land-use-label"] },
    ];

    for (const { defId, mapLayers } of layerMappings) {
      const layerDef = layers.find((l) => l.id === defId);
      const visibility = layerDef?.visible ? "visible" : "none";
      for (const ml of mapLayers) {
        if (map.getLayer(ml)) {
          map.setLayoutProperty(ml, "visibility", visibility);
        }
      }
    }

    return () => {
      popupRef.current?.remove();
      for (const lid of addedLayers) {
        if (map.getLayer(lid)) map.removeLayer(lid);
      }
      for (const sid of addedSources) {
        if (map.getSource(sid)) map.removeSource(sid);
      }
    };
  }, [map, overlayItems, layers]);

  return { layers, toggleLayer };
}
