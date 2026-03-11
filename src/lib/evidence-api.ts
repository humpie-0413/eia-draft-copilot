import { api } from "./api-client";
import type { PaginatedList, PaginationParams } from "@/types/api";
import type {
  Evidence,
  EvidenceFilter,
  SourceSnapshot,
} from "@/types/evidence";

/** 쿼리 파라미터 문자열 생성 */
function toQueryString(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== "",
  );
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(
    entries.map(([k, v]) => [k, String(v)]),
  ).toString();
}

// ─── 증거 API ───

/** 프로젝트별 증거 목록 조회 */
export async function listEvidences(
  projectId: string,
  filter?: EvidenceFilter,
  pagination?: PaginationParams,
): Promise<PaginatedList<Evidence>> {
  const qs = toQueryString({
    project_id: projectId,
    category: filter?.category,
    screening_only: filter?.screening_only,
    data_source_id: filter?.data_source_id,
    skip: pagination?.skip,
    limit: pagination?.limit,
  });
  return api.get(`/api/v1/evidences${qs}`);
}

/** 증거 상세 조회 */
export async function getEvidence(evidenceId: string): Promise<Evidence> {
  return api.get(`/api/v1/evidences/${evidenceId}`);
}

/** 증거 생성 */
export async function createEvidence(
  data: Record<string, unknown>,
): Promise<Evidence> {
  return api.post("/api/v1/evidences", data);
}

/** 증거 수정 */
export async function updateEvidence(
  evidenceId: string,
  data: Record<string, unknown>,
): Promise<Evidence> {
  return api.patch(`/api/v1/evidences/${evidenceId}`, data);
}

/** 증거 삭제 */
export async function deleteEvidence(evidenceId: string): Promise<void> {
  return api.delete(`/api/v1/evidences/${evidenceId}`);
}

// ─── 스냅샷 API ───

/** 스냅샷 상세 조회 (raw_payload 포함) */
export async function getSnapshot(snapshotId: string): Promise<SourceSnapshot> {
  return api.get(`/api/v1/snapshots/${snapshotId}`);
}
