import { api } from "./api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** 도면 유형 */
export interface MapType {
  map_type: string;
  title: string;
}

/** 도면 목록 응답 */
export interface MapListResponse {
  maps: MapType[];
}

/** 버퍼 분석 응답 */
export interface BufferResponse {
  project_id: string;
  radius_m: number;
  buffer_geojson: object;
  centroid: number[];
  area_km2: number;
}

/** 오버레이 항목 */
export interface OverlayItem {
  name: string;
  item_type: string;
  category: string;
  distance_m: number;
  lat: number;
  lon: number;
  metadata: Record<string, string>;
}

/** 오버레이 분석 응답 */
export interface OverlayResponse {
  project_id: string;
  radius_m: number;
  items: OverlayItem[];
  total_count: number;
}

/** 도면 목록 조회 */
export function getMapList(projectId: string): Promise<MapListResponse> {
  return api.get(`/api/v1/projects/${projectId}/maps`);
}

/** 도면 PNG URL 반환 */
export function getMapImageUrl(projectId: string, mapType: string): string {
  return `${API_BASE}/api/v1/projects/${projectId}/maps/${mapType}`;
}

/** 버퍼 분석 */
export function getBuffer(
  projectId: string,
  radius: number = 1000,
): Promise<BufferResponse> {
  return api.get(`/api/v1/projects/${projectId}/spatial/buffer?radius=${radius}`);
}

/** 중첩 분석 */
export function getOverlay(
  projectId: string,
  radius: number = 1000,
): Promise<OverlayResponse> {
  return api.get(
    `/api/v1/projects/${projectId}/spatial/overlay?radius=${radius}`,
  );
}
