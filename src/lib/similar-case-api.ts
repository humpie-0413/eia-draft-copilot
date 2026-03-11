import { api } from "./api-client";
import type { PaginatedList, PaginationParams } from "@/types/api";
import type {
  SimilarCase,
  SimilarCaseMatchList,
} from "@/types/similar-case";

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

// ─── 유사사례 CRUD ───

/** 유사사례 목록 조회 */
export async function listSimilarCases(
  projectType?: string,
  pagination?: PaginationParams,
): Promise<PaginatedList<SimilarCase>> {
  const qs = toQueryString({
    project_type: projectType,
    skip: pagination?.skip,
    limit: pagination?.limit,
  });
  return api.get(`/api/v1/similar-cases${qs}`);
}

/** 유사사례 상세 조회 */
export async function getSimilarCase(caseId: string): Promise<SimilarCase> {
  return api.get(`/api/v1/similar-cases/${caseId}`);
}

// ─── 유사사례 매칭 ───

/** 프로젝트별 유사사례 매칭 검색 */
export async function matchSimilarCases(
  projectId: string,
  options?: { top_k?: number; min_score?: number },
): Promise<SimilarCaseMatchList> {
  const qs = toQueryString({
    top_k: options?.top_k,
    min_score: options?.min_score,
  });
  return api.get(`/api/v1/similar-cases/match/${projectId}${qs}`);
}
