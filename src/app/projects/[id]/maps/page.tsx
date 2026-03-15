"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getMapList, getMapImageUrl } from "@/lib/spatial-api";
import type { MapType } from "@/lib/spatial-api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, Map, Maximize2, X } from "lucide-react";

export default function MapsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [maps, setMaps] = useState<MapType[]>([]);
  const [loading, setLoading] = useState(true);
  const [fullscreenMap, setFullscreenMap] = useState<string | null>(null);
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());

  const fetchMaps = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMapList(projectId);
      setMaps(res.maps);
    } catch (err) {
      console.error("도면 목록 조회 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchMaps();
  }, [fetchMaps]);

  const handleDownload = async (mapType: string, title: string) => {
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
      console.error(`다운로드 실패: ${title}`, err);
    }
  };

  const handleImageError = (mapType: string) => {
    setImageErrors((prev) => new Set(prev).add(mapType));
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Map className="h-6 w-6" />
              GIS 도면
            </h2>
            <p className="text-sm text-muted-foreground">
              사업대상지 공간 분석 도면 — {maps.length}종
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="outline" size="sm">
              초안 뼈대
            </Button>
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="py-16 text-center text-muted-foreground">
          도면 목록을 불러오는 중…
        </p>
      ) : (
        <>
          {/* 도면 그리드 */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {maps.map((m) => (
              <div
                key={m.map_type}
                className="group relative overflow-hidden rounded-lg border bg-card"
              >
                {/* 도면 이미지 */}
                <div className="relative aspect-[4/3] bg-muted">
                  {imageErrors.has(m.map_type) ? (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                      <div className="text-center">
                        <Map className="mx-auto h-12 w-12 opacity-30" />
                        <p className="mt-2 text-sm">
                          도면 생성에 geometry가 필요합니다
                        </p>
                      </div>
                    </div>
                  ) : (
                    <img
                      src={getMapImageUrl(projectId, m.map_type)}
                      alt={m.title}
                      className="h-full w-full object-contain"
                      onError={() => handleImageError(m.map_type)}
                    />
                  )}

                  {/* 오버레이 버튼 */}
                  {!imageErrors.has(m.map_type) && (
                    <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setFullscreenMap(m.map_type)}
                      >
                        <Maximize2 className="mr-1 h-4 w-4" />
                        전체 화면
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleDownload(m.map_type, m.title)}
                      >
                        <Download className="mr-1 h-4 w-4" />
                        PNG
                      </Button>
                    </div>
                  )}
                </div>

                {/* 제목 */}
                <div className="p-3">
                  <h3 className="font-medium">{m.title}</h3>
                  <Badge variant="outline" className="mt-1 text-xs">
                    {m.map_type}
                  </Badge>
                </div>
              </div>
            ))}
          </div>

          {maps.length === 0 && (
            <div className="rounded-md border border-dashed p-12 text-center text-muted-foreground">
              <Map className="mx-auto h-12 w-12 opacity-30" />
              <p className="mt-3 text-lg font-medium">도면이 없습니다</p>
              <p className="mt-1 text-sm">
                프로젝트에 geometry를 등록하면 도면을 생성할 수 있습니다.
              </p>
            </div>
          )}
        </>
      )}

      {/* 전체 화면 모달 */}
      {fullscreenMap && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setFullscreenMap(null)}
        >
          <div className="relative max-h-[90vh] max-w-[90vw]">
            <Button
              variant="ghost"
              size="icon"
              className="absolute -right-12 -top-12 text-white hover:bg-white/20"
              onClick={() => setFullscreenMap(null)}
            >
              <X className="h-6 w-6" />
            </Button>
            <img
              src={getMapImageUrl(projectId, fullscreenMap)}
              alt="전체 화면 도면"
              className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="mt-2 flex justify-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  const m = maps.find((m) => m.map_type === fullscreenMap);
                  if (m) handleDownload(m.map_type, m.title);
                }}
              >
                <Download className="mr-1 h-4 w-4" />
                PNG 다운로드
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
