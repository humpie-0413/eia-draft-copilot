"use client";

import type { QaSummary } from "@/types/qa";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

interface QaSummaryBarProps {
  summary: QaSummary;
  exportReady: boolean;
}

export function QaSummaryBar({ summary, exportReady }: QaSummaryBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border p-4">
      {/* export 상태 */}
      <div className="flex items-center gap-2">
        {exportReady ? (
          <>
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <span className="text-sm font-medium text-green-700">
              Export 가능
            </span>
          </>
        ) : (
          <>
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-sm font-medium text-red-700">
              Export 차단
            </span>
          </>
        )}
      </div>

      <div className="h-6 w-px bg-border" />

      {/* 심각도별 카운트 */}
      <div className="flex items-center gap-1">
        <AlertCircle className="h-4 w-4 text-red-500" />
        <span className="text-sm">
          심각 <strong>{summary.critical_count}</strong>
        </span>
      </div>
      <div className="flex items-center gap-1">
        <AlertTriangle className="h-4 w-4 text-yellow-500" />
        <span className="text-sm">
          경고 <strong>{summary.warning_count}</strong>
        </span>
      </div>
      <div className="flex items-center gap-1">
        <Info className="h-4 w-4 text-blue-500" />
        <span className="text-sm">
          참고 <strong>{summary.info_count}</strong>
        </span>
      </div>

      <div className="h-6 w-px bg-border" />

      <span className="text-sm text-muted-foreground">
        총 {summary.total}건
      </span>
    </div>
  );
}
