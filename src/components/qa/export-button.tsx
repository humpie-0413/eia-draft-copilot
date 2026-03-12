"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { downloadDocx, downloadPdf } from "@/lib/qa-api";
import { Download, Loader2, AlertCircle, ChevronDown } from "lucide-react";

type ExportFormat = "docx" | "pdf";

interface ExportButtonProps {
  projectId: string;
  exportReady: boolean;
  criticalCount: number;
}

export function ExportButton({
  projectId,
  exportReady,
  criticalCount,
}: ExportButtonProps) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const handleDownload = async (format: ExportFormat) => {
    setError(null);
    setMenuOpen(false);
    setDownloading(true);
    try {
      if (format === "pdf") {
        await downloadPdf(projectId);
      } else {
        await downloadDocx(projectId);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "다운로드에 실패했습니다.",
      );
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <div className="flex">
          {/* 기본 DOCX 다운로드 버튼 */}
          <Button
            onClick={() => handleDownload("docx")}
            disabled={!exportReady || downloading}
            variant={exportReady ? "default" : "outline"}
            className="rounded-r-none"
          >
            {downloading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {downloading ? "생성 중…" : "Export"}
          </Button>

          {/* 형식 선택 드롭다운 */}
          <Button
            onClick={() => setMenuOpen(!menuOpen)}
            disabled={!exportReady || downloading}
            variant={exportReady ? "default" : "outline"}
            className="rounded-l-none border-l border-l-white/20 px-2"
            aria-label="Export 형식 선택"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>

        {/* 드롭다운 메뉴 */}
        {menuOpen && (
          <div className="absolute right-0 top-full z-10 mt-1 w-40 rounded-md border bg-white shadow-lg dark:bg-gray-800 dark:border-gray-700">
            <button
              onClick={() => handleDownload("docx")}
              className="flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded-t-md"
            >
              <Download className="h-4 w-4" />
              DOCX 다운로드
            </button>
            <button
              onClick={() => handleDownload("pdf")}
              className="flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded-b-md"
            >
              <Download className="h-4 w-4" />
              PDF 다운로드
            </button>
          </div>
        )}
      </div>

      {!exportReady && (
        <span className="flex items-center gap-1 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          critical 이슈 {criticalCount}건 미해결
        </span>
      )}

      {error && (
        <span className="text-sm text-red-600">{error}</span>
      )}
    </div>
  );
}
