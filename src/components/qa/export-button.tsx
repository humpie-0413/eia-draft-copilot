"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { downloadDocx } from "@/lib/qa-api";
import { Download, Loader2, AlertCircle } from "lucide-react";

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

  const handleDownload = async () => {
    setError(null);
    setDownloading(true);
    try {
      await downloadDocx(projectId);
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
      <Button
        onClick={handleDownload}
        disabled={!exportReady || downloading}
        variant={exportReady ? "default" : "outline"}
      >
        {downloading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Download className="mr-2 h-4 w-4" />
        )}
        {downloading ? "생성 중…" : "DOCX 다운로드"}
      </Button>

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
