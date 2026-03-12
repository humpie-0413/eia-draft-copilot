import { api } from "./api-client";
import type { QaResult, ExportReady } from "@/types/qa";
import type { ExportPreview, ExportOptions } from "@/types/export";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** QA 규칙 엔진 실행 결과 조회 */
export async function getQaResult(projectId: string): Promise<QaResult> {
  return api.get(`/api/v1/projects/${projectId}/qa`);
}

/** export 가능 여부 간략 확인 */
export async function checkExportReady(
  projectId: string,
): Promise<ExportReady> {
  return api.get(`/api/v1/projects/${projectId}/qa/export-ready`);
}

/** Export 미리보기 조회 */
export async function getExportPreview(
  projectId: string,
): Promise<ExportPreview> {
  return api.get(`/api/v1/projects/${projectId}/export/preview`);
}

/** 파일 다운로드 공통 처리 */
async function downloadFile(
  url: string,
  method: "GET" | "POST",
  defaultFilename: string,
): Promise<void> {
  const res = await fetch(url, { method });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "다운로드에 실패했습니다.");
  }

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  let filename = defaultFilename;
  if (disposition) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match) filename = match[1];
  }

  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

/** 옵션을 쿼리 문자열로 변환 */
function optionsToParams(options?: ExportOptions): string {
  if (!options) return "";
  const params = new URLSearchParams();
  params.set("include_appendix_a", String(options.include_appendix_a));
  params.set("include_appendix_b", String(options.include_appendix_b));
  params.set("include_appendix_c", String(options.include_appendix_c));
  return `?${params.toString()}`;
}

/** DOCX 파일 다운로드 */
export async function downloadDocx(
  projectId: string,
  options?: ExportOptions,
): Promise<void> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/export/docx${optionsToParams(options)}`;
  return downloadFile(url, "POST", "EIA_report.docx");
}

/** PDF 파일 다운로드 */
export async function downloadPdf(
  projectId: string,
  options?: ExportOptions,
): Promise<void> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/export/pdf${optionsToParams(options)}`;
  return downloadFile(url, "GET", "EIA_report.pdf");
}
