/** 섹션 상태 */
export type SectionStatusValue = "empty" | "partial" | "complete";

/** 개별 지표 충족 상태 */
export interface IndicatorStatus {
  name: string;
  fulfilled: boolean;
  evidence_count: number;
}

/** 섹션 정의 */
export interface SectionDefinition {
  key: string;
  title: string;
  description: string;
  evidence_category: string;
  required_indicators: string[];
  order: number;
}

/** 섹션별 증거 충족 상태 */
export interface SectionStatus {
  section_key: string;
  title: string;
  description: string;
  order: number;
  total_evidence_count: number;
  required_indicators: IndicatorStatus[];
  fulfilled_count: number;
  required_count: number;
  coverage_ratio: number;
  status: SectionStatusValue;
}

/** 전체 섹션 상태 목록 */
export interface SectionStatusList {
  project_id: string;
  sections: SectionStatus[];
  total_sections: number;
}

/** 초안 뼈대에 배치된 근거 항목 */
export interface EvidenceEntry {
  evidence_id: string;
  indicator: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  observed_at: string | null;
  data_source_id: string | null;
  metadata_json: Record<string, unknown> | null;
}

/** 초안 뼈대 섹션 */
export interface ScaffoldSection {
  section_key: string;
  title: string;
  description: string;
  order: number;
  evidence_entries: EvidenceEntry[];
  summary_text: string;
}

/** 초안 뼈대 전체 */
export interface DraftScaffold {
  project_id: string;
  generated_at: string;
  sections: ScaffoldSection[];
  total_evidence_count: number;
}

/** 섹션 상태별 한글 라벨 */
export const SECTION_STATUS_LABELS: Record<SectionStatusValue, string> = {
  empty: "미수집",
  partial: "일부 충족",
  complete: "충족",
};
