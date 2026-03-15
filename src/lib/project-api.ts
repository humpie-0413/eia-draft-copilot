import { api } from "./api-client";
import type { Project } from "@/types/project";

/** 프로젝트 단건 조회 */
export function getProject(projectId: string): Promise<Project> {
  return api.get(`/api/v1/projects/${projectId}`);
}

/** 프로젝트 geometry 업데이트 */
export function updateProjectGeometry(
  projectId: string,
  geometry: GeoJSON.Geometry | null,
): Promise<Project> {
  return api.patch(`/api/v1/projects/${projectId}`, { geometry });
}
