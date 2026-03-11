/** 유사사례 (서버 응답) */
export interface SimilarCase {
  id: string;
  name: string;
  description: string | null;
  project_type: string;
  location: Record<string, unknown> | null;
  area_sqm: number | null;
  completed_at: string | null;
  summary: string | null;
  key_findings: Record<string, unknown> | null;
  evidence_categories: string[] | null;
  source_url: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

/** 유사사례 매칭 결과 — 유사도 점수 포함 */
export interface SimilarCaseMatch {
  similar_case: SimilarCase;
  overall_score: number;
  type_score: number;
  location_score: number;
  scale_score: number;
  category_score: number;
}

/** 프로젝트별 유사사례 매칭 결과 목록 */
export interface SimilarCaseMatchList {
  project_id: string;
  matches: SimilarCaseMatch[];
  total: number;
}
