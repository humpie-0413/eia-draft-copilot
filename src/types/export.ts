/** Export 미리보기 섹션 정보 */
export interface ExportPreviewSection {
  title: string;
  state: string;
  evidence_count: number;
  has_stats: boolean;
  has_standards: boolean;
}

/** Export 미리보기 응답 */
export interface ExportPreview {
  project_name: string;
  project_type: string | null;
  centroid: [number, number] | null;
  sections: ExportPreviewSection[];
  total_evidence: number;
  similar_case_count: number;
  qa_issue_count: number;
  export_ready: boolean;
}

/** Export 옵션 */
export interface ExportOptions {
  include_appendix_a: boolean;
  include_appendix_b: boolean;
  include_appendix_c: boolean;
}
