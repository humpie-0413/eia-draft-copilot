/** 커넥터 정보 */
export interface ConnectorInfo {
  connector_key: string;
  display_name: string;
}

/** 수집 요청 */
export interface CollectRequest {
  project_id: string;
  params: Record<string, string | number>;
  screening_only?: boolean;
}

/** 수집 결과 */
export interface CollectResult {
  connector_key: string;
  snapshot_id: string;
  status: "success" | "error" | "partial";
  evidence_count: number;
  error_message: string | null;
}
