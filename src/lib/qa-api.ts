import { api } from "./api-client";
import type { QaResult, ExportReady } from "@/types/qa";

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

/** DOCX 파일 다운로드 */
export async function downloadDocx(projectId: string): Promise<void> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/export/docx`;
  return downloadFile(url, "POST", "EIA_report.docx");
}

/** PDF 파일 다운로드 */
export async function downloadPdf(projectId: string): Promise<void> {
  const url = `${API_BASE}/api/v1/projects/${projectId}/export/pdf`;
  return downloadFile(url, "GET", "EIA_report.pdf");
}
