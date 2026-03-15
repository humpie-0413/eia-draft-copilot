"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import maplibregl from "maplibre-gl";
import { BaseMap } from "@/components/map/base-map";
import { LayerControl } from "@/components/map/layer-control";
import { DrawTools } from "@/components/map/draw-tools";
import { useMapLayers } from "@/components/map/use-map-layers";
import { getProject, updateProjectGeometry } from "@/lib/project-api";
import {
  getBuffer,
  getOverlay,
  getMapImageUrl,
  getMapList,
} from "@/lib/spatial-api";
import type {
  BufferResponse,
  OverlayItem,
  OverlayResponse,
  MapType as StaticMapType,
} from "@/lib/spatial-api";
import type { Project } from "@/types/project";
import { PROJECT_TYPE_LABELS } from "@/types/project";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Download,
  Layers,
  Map,
  MapPin,
  Pencil,
  Save,
} from "lucide-react";

export default function ProjectMapPage() {
  const params = useParams();
  const projectId = params.id as string;

  // 상태
  const [project, setProject] = useState<Project | null>(null);
  const [mapInstance, setMapInstance] = useState<maplibregl.Map | null>(null);
  const [buffer1km, setBuffer1km] = useState<BufferResponse | null>(null);
  const [buffer5km, setBuffer5km] = useState<BufferResponse | null>(null);
  const [overlayItems, setOverlayItems] = useState<OverlayItem[]>([]);
  const [overlayResponse, setOverlayResponse] =
    useState<OverlayResponse | null>(null);
  const [staticMaps, setStaticMaps] = useState<StaticMapType[]>([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [drawnGeometry, setDrawnGeometry] =
    useState<GeoJSON.Polygon | null>(null);
  const [saving, setSaving] = useState(false);

  // 프로젝트 + 공간 데이터 로딩
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const proj = await getProject(projectId);
        setProject(proj);

        // 공간 데이터 병렬 로딩
        const results = await Promise.allSettled([
          getBuffer(projectId, 1000),
          getBuffer(projectId, 5000),
          getOverlay(projectId, 5000),
          getMapList(projectId),
        ]);

        if (results[0].status === "fulfilled") setBuffer1km(results[0].value);
        if (results[1].status === "fulfilled") setBuffer5km(results[1].value);
        if (results[2].status === "fulfilled") {
          setOverlayResponse(results[2].value);
          setOverlayItems(results[2].value.items);
        }
        if (results[3].status === "fulfilled")
          setStaticMaps(results[3].value.maps);
      } catch (err) {
        console.error("데이터 로딩 실패:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [projectId]);

  // 지도 레이어 관리
  const geometry = project?.geometry as GeoJSON.Geometry | null | undefined;
  const { layers, toggleLayer } = useMapLayers({
    map: mapInstance,
    geometry: editMode ? undefined : geometry,
    buffer1km,
    buffer5km,
    overlayItems,
  });

  const handleMapReady = useCallback((map: maplibregl.Map) => {
    setMapInstance(map);
  }, []);

  // Geometry 저장
  const handleSaveGeometry = async () => {
    if (!drawnGeometry) return;
    setSaving(true);
    try {
      const updated = await updateProjectGeometry(projectId, drawnGeometry);
      setProject(updated);
      setEditMode(false);
      setDrawnGeometry(null);
      // 공간 데이터 재로딩
      const [buf1, buf5, overlay] = await Promise.allSettled([
        getBuffer(projectId, 1000),
        getBuffer(projectId, 5000),
        getOverlay(projectId, 5000),
      ]);
      if (buf1.status === "fulfilled") setBuffer1km(buf1.value);
      if (buf5.status === "fulfilled") setBuffer5km(buf5.value);
      if (overlay.status === "fulfilled") {
        setOverlayResponse(overlay.value);
        setOverlayItems(overlay.value.items);
      }
    } catch (err) {
      console.error("geometry 저장 실패:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDrawComplete = useCallback((geo: GeoJSON.Polygon | null) => {
    setDrawnGeometry(geo);
  }, []);

  // 정적 도면 다운로드
  const handleDownloadMap = async (mapType: string) => {
    const url = getMapImageUrl(projectId, mapType);
    try {
      const res = await fetch(url);
      if (!res.ok) return;
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${projectId}_${mapType}.png`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      console.error("도면 다운로드 실패:", err);
    }
  };

  return (
    <div className="flex h-[calc(100vh-80px)] gap-0">
      {/* 사이드 패널 */}
      <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-r bg-white">
        {/* 헤더 */}
        <div className="border-b p-4">
          <div className="flex items-center gap-2">
            <Link href={`/projects`}>
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className="min-w-0">
              <h2 className="truncate text-lg font-bold">
                {project?.name || "프로젝트 지도"}
              </h2>
              {project?.project_type && (
                <Badge variant="outline" className="text-xs">
                  {PROJECT_TYPE_LABELS[project.project_type] ||
                    project.project_type}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* 사업 경계 편집 */}
        <div className="border-b p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-medium">
              <MapPin className="h-4 w-4" />
              사업 경계
            </h3>
            <Button
              variant={editMode ? "default" : "outline"}
              size="sm"
              onClick={() => setEditMode(!editMode)}
            >
              <Pencil className="mr-1 h-3.5 w-3.5" />
              {editMode ? "편집 취소" : "편집"}
            </Button>
          </div>

          {editMode && (
            <div className="space-y-2">
              <DrawTools
                map={mapInstance}
                initialGeometry={
                  geometry?.type === "Polygon"
                    ? (geometry as GeoJSON.Polygon)
                    : null
                }
                onDrawComplete={handleDrawComplete}
              />
              {drawnGeometry && (
                <Button
                  size="sm"
                  className="w-full"
                  onClick={handleSaveGeometry}
                  disabled={saving}
                >
                  <Save className="mr-1.5 h-3.5 w-3.5" />
                  {saving ? "저장 중…" : "geometry 저장"}
                </Button>
              )}
            </div>
          )}

          {!editMode && geometry && (
            <p className="text-xs text-muted-foreground">
              geometry 타입: {geometry.type}
            </p>
          )}
          {!editMode && !geometry && (
            <p className="text-xs text-orange-600">
              geometry가 등록되지 않았습니다. 편집 버튼을 눌러 사업 경계를
              그리세요.
            </p>
          )}
        </div>

        {/* 레이어 컨트롤 */}
        <div className="p-4">
          <LayerControl layers={layers} onToggle={toggleLayer} />
        </div>

        {/* 버퍼 내 규제 항목 */}
        {overlayResponse && overlayResponse.items.length > 0 && (
          <div className="border-t p-4 space-y-2">
            <h3 className="flex items-center gap-1.5 text-sm font-medium">
              <Layers className="h-4 w-4" />
              버퍼 내 항목 ({overlayResponse.total_count}건)
            </h3>
            <div className="max-h-60 space-y-1 overflow-y-auto">
              {overlayResponse.items.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start justify-between rounded border px-2 py-1.5 text-xs"
                >
                  <div>
                    <span className="font-medium">{item.name}</span>
                    <span className="ml-1 text-gray-500">{item.item_type}</span>
                  </div>
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    {Math.round(item.distance_m)}m
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 정적 도면 다운로드 */}
        {staticMaps.length > 0 && (
          <div className="border-t p-4 space-y-2">
            <h3 className="flex items-center gap-1.5 text-sm font-medium">
              <Map className="h-4 w-4" />
              정적 도면 ({staticMaps.length}종)
            </h3>
            <div className="space-y-1">
              {staticMaps.map((m) => (
                <Button
                  key={m.map_type}
                  variant="outline"
                  size="sm"
                  className="w-full justify-start text-xs"
                  onClick={() => handleDownloadMap(m.map_type)}
                >
                  <Download className="mr-1.5 h-3 w-3" />
                  {m.title}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* 네비게이션 */}
        <div className="mt-auto border-t p-4 space-y-1">
          <Link href={`/projects/${projectId}/maps`}>
            <Button variant="ghost" size="sm" className="w-full justify-start">
              <Map className="mr-2 h-4 w-4" />
              정적 도면 보기
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/evidences`}>
            <Button variant="ghost" size="sm" className="w-full justify-start">
              증거 작업대
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="ghost" size="sm" className="w-full justify-start">
              초안 뼈대
            </Button>
          </Link>
        </div>
      </aside>

      {/* 지도 영역 */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            지도 데이터를 불러오는 중…
          </div>
        ) : (
          <BaseMap
            geometry={geometry}
            onMapReady={handleMapReady}
            className="h-full w-full"
          />
        )}
      </div>
    </div>
  );
}
