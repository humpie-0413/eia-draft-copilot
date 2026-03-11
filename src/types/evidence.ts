/** 환경영향평가 증거 분야 */
export const EVIDENCE_CATEGORIES = {
  air_quality: "대기질",
  water_quality: "수질",
  noise_vibration: "소음·진동",
  ecology: "생태",
  soil: "토양",
  waste: "폐기물",
  landscape: "경관",
  cultural_heritage: "문화재",
  climate: "기후",
  land_use: "토지이용",
  traffic: "교통",
  other: "기타",
} as const;

export type EvidenceCategory = keyof typeof EVIDENCE_CATEGORIES;

/** GeoJSON Point */
export interface GeoJsonPoint {
  type: "Point";
  coordinates: [number, number];
}

/** 증거 데이터 (서버 응답) */
export interface Evidence {
  id: string;
  project_id: string;
  snapshot_id: string | null;
  data_source_id: string | null;
  category: EvidenceCategory;
  indicator: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  observed_at: string | null;
  location: GeoJsonPoint | null;
  metadata_json: Record<string, unknown> | null;
  screening_only: boolean;
  created_at: string;
}

/** 증거 생성/수정 폼 데이터 */
export interface EvidenceFormData {
  category: EvidenceCategory;
  indicator: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  observed_at: string | null;
  screening_only: boolean;
  metadata_json: string; // JSON 문자열로 입력받음
}

/** 증거 필터 */
export interface EvidenceFilter {
  category?: EvidenceCategory;
  screening_only?: boolean;
  data_source_id?: string;
}

/** 소스 스냅샷 */
export interface SourceSnapshot {
  id: string;
  data_source_id: string;
  project_id: string;
  query_params: Record<string, unknown> | null;
  raw_payload: Record<string, unknown>;
  status: "success" | "error" | "partial";
  error_message: string | null;
  fetched_at: string;
  created_at: string;
}

/** 데이터 소스 */
export interface DataSource {
  id: string;
  name: string;
  connector_key: string;
  base_url: string | null;
  description: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}
