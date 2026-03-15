"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

/** 한국 중심 기본값 */
const DEFAULT_CENTER: [number, number] = [127.0, 37.5];
const DEFAULT_ZOOM = 10;

/** 무료 배경지도 스타일 (OpenFreeMap) */
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

export interface BaseMapProps {
  /** 초기 중심점 [lng, lat] */
  center?: [number, number];
  /** 초기 줌 레벨 */
  zoom?: number;
  /** geometry GeoJSON — centroid + bounds 자동 계산용 */
  geometry?: GeoJSON.Geometry | null;
  /** 지도 준비 완료 콜백 */
  onMapReady?: (map: maplibregl.Map) => void;
  /** CSS 클래스 */
  className?: string;
  /** 지도 컨트롤 비활성화 (미니맵용) */
  minimal?: boolean;
}

/** geometry의 bounding box를 계산한다. */
function getGeometryBounds(
  geometry: GeoJSON.Geometry,
): maplibregl.LngLatBoundsLike | null {
  const coords: number[][] = [];

  function extractCoords(g: GeoJSON.Geometry) {
    switch (g.type) {
      case "Point":
        coords.push(g.coordinates as number[]);
        break;
      case "MultiPoint":
      case "LineString":
        (g.coordinates as number[][]).forEach((c) => coords.push(c));
        break;
      case "MultiLineString":
      case "Polygon":
        (g.coordinates as number[][][]).forEach((ring) =>
          ring.forEach((c) => coords.push(c)),
        );
        break;
      case "MultiPolygon":
        (g.coordinates as number[][][][]).forEach((poly) =>
          poly.forEach((ring) => ring.forEach((c) => coords.push(c))),
        );
        break;
      case "GeometryCollection":
        g.geometries.forEach(extractCoords);
        break;
    }
  }

  extractCoords(geometry);

  if (coords.length === 0) return null;

  let minLng = Infinity,
    minLat = Infinity,
    maxLng = -Infinity,
    maxLat = -Infinity;

  for (const [lng, lat] of coords) {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }

  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}

/** geometry의 centroid를 계산한다. */
function getGeometryCentroid(
  geometry: GeoJSON.Geometry,
): [number, number] | null {
  const bounds = getGeometryBounds(geometry);
  if (!bounds) return null;
  const [[minLng, minLat], [maxLng, maxLat]] = bounds as [
    [number, number],
    [number, number],
  ];
  return [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
}

/**
 * MapLibre GL JS 기본 지도 래퍼 컴포넌트.
 * 프로젝트 geometry가 주어지면 자동으로 centroid + bounds에 맞춤.
 */
export function BaseMap({
  center,
  zoom,
  geometry,
  onMapReady,
  className = "h-full w-full",
  minimal = false,
}: BaseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [loaded, setLoaded] = useState(false);

  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return;

    // 초기 중심점 결정
    let initCenter = center ?? DEFAULT_CENTER;
    let initZoom = zoom ?? DEFAULT_ZOOM;

    if (geometry) {
      const centroid = getGeometryCentroid(geometry);
      if (centroid) initCenter = centroid;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: initCenter,
      zoom: initZoom,
      attributionControl: minimal ? false : undefined,
    });

    // 지도 컨트롤 추가
    if (!minimal) {
      map.addControl(new maplibregl.NavigationControl(), "top-right");
      map.addControl(
        new maplibregl.ScaleControl({ maxWidth: 200, unit: "metric" }),
        "bottom-left",
      );
    }

    map.on("load", () => {
      // geometry가 있으면 bounds에 맞춤
      if (geometry) {
        const bounds = getGeometryBounds(geometry);
        if (bounds) {
          map.fitBounds(bounds, { padding: 60, maxZoom: 16 });
        }
      }

      setLoaded(true);
      onMapReady?.(map);
    });

    mapRef.current = map;
  }, [center, zoom, geometry, onMapReady, minimal]);

  useEffect(() => {
    initMap();
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      setLoaded(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // geometry 변경 시 지도 위치 업데이트
  useEffect(() => {
    if (!mapRef.current || !loaded || !geometry) return;
    const bounds = getGeometryBounds(geometry);
    if (bounds) {
      mapRef.current.fitBounds(bounds, { padding: 60, maxZoom: 16 });
    }
  }, [geometry, loaded]);

  return (
    <div ref={containerRef} className={className} />
  );
}

export { getGeometryBounds, getGeometryCentroid };
