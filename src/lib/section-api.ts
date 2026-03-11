import { api } from "./api-client";
import type {
  DraftScaffold,
  ScaffoldSection,
  SectionDefinition,
  SectionStatus,
  SectionStatusList,
} from "@/types/section";

// ─── 섹션 정의 ───

/** 섹션 정의 목록 조회 */
export async function listSectionDefinitions(
  projectId: string,
): Promise<SectionDefinition[]> {
  return api.get(`/api/v1/projects/${projectId}/sections/definitions`);
}

// ─── 섹션 상태 ───

/** 전체 섹션 상태 조회 */
export async function getSectionsStatus(
  projectId: string,
): Promise<SectionStatusList> {
  return api.get(`/api/v1/projects/${projectId}/sections/status`);
}

/** 개별 섹션 상태 조회 */
export async function getSectionStatus(
  projectId: string,
  sectionKey: string,
): Promise<SectionStatus> {
  return api.get(`/api/v1/projects/${projectId}/sections/status/${sectionKey}`);
}

// ─── 초안 뼈대 ───

/** 전체 초안 뼈대 조회 */
export async function getDraftScaffold(
  projectId: string,
): Promise<DraftScaffold> {
  return api.get(`/api/v1/projects/${projectId}/sections/scaffold`);
}

/** 개별 섹션 초안 뼈대 조회 */
export async function getSectionScaffold(
  projectId: string,
  sectionKey: string,
): Promise<ScaffoldSection> {
  return api.get(
    `/api/v1/projects/${projectId}/sections/scaffold/${sectionKey}`,
  );
}
