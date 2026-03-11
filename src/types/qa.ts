/** QA 이슈 심각도 */
export type QaSeverity = "critical" | "warning" | "info";

/** 단일 QA 이슈 */
export interface QaIssue {
  rule_id: string;
  severity: QaSeverity;
  section_key: string | null;
  title: string;
  message: string;
  indicators: string[];
}

/** QA 요약 통계 */
export interface QaSummary {
  critical_count: number;
  warning_count: number;
  info_count: number;
  total: number;
}

/** QA 실행 결과 */
export interface QaResult {
  project_id: string;
  run_at: string;
  issues: QaIssue[];
  summary: QaSummary;
  export_ready: boolean;
}

/** export 가능 여부 간략 응답 */
export interface ExportReady {
  project_id: string;
  export_ready: boolean;
  critical_count: number;
  message: string;
}

/** 심각도별 한글 라벨 */
export const SEVERITY_LABELS: Record<QaSeverity, string> = {
  critical: "심각",
  warning: "경고",
  info: "참고",
};

/** 심각도별 색상 클래스 */
export const SEVERITY_COLORS: Record<QaSeverity, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
  info: "bg-blue-100 text-blue-800 border-blue-200",
};
