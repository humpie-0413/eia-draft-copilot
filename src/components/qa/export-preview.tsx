"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { getExportPreview } from "@/lib/qa-api";
import type { ExportPreview, ExportOptions } from "@/types/export";
import {
  FileText,
  BookOpen,
  Database,
  GitCompare,
  ShieldCheck,
  Loader2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  MinusCircle,
} from "lucide-react";

interface ExportPreviewPanelProps {
  projectId: string;
  options: ExportOptions;
  onOptionsChange: (options: ExportOptions) => void;
}

const STATE_ICON: Record<string, typeof CheckCircle2> = {
  "완료": CheckCircle2,
  "미비": AlertTriangle,
  "미수집": MinusCircle,
};

const STATE_COLOR: Record<string, string> = {
  "완료": "text-green-600",
  "미비": "text-yellow-600",
  "미수집": "text-red-500",
};

export function ExportPreviewPanel({
  projectId,
  options,
  onOptionsChange,
}: ExportPreviewPanelProps) {
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  const fetchPreview = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getExportPreview(projectId);
      setPreview(data);
    } catch {
      // 미리보기 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchPreview();
  }, [fetchPreview]);

  if (loading) {
    return (
      <div className="rounded-lg border bg-muted/30 p-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          문서 구조 분석 중...
        </div>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div className="rounded-lg border bg-card">
      {/* 헤더 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium text-sm">문서 구조 미리보기</span>
          <Badge variant="outline" className="text-xs">
            {preview.total_evidence}건 증거
          </Badge>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="border-t px-4 pb-4">
          {/* 문서 구조 트리 */}
          <div className="mt-3 space-y-1 text-sm">
            {/* 표지 */}
            <div className="flex items-center gap-2 py-1 pl-2">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">표지</span>
              <span className="text-xs text-muted-foreground">
                — {preview.project_name}
                {preview.project_type && ` (${preview.project_type})`}
              </span>
            </div>

            {/* 목차 */}
            <div className="flex items-center gap-2 py-1 pl-2">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">목차</span>
            </div>

            {/* 본문 섹션 */}
            {preview.sections.map((section, idx) => {
              const Icon = STATE_ICON[section.state] || MinusCircle;
              const colorClass = STATE_COLOR[section.state] || "text-gray-400";
              return (
                <div key={idx} className="flex items-center gap-2 py-1 pl-4">
                  <Icon className={`h-3.5 w-3.5 ${colorClass}`} />
                  <span>{section.title}</span>
                  <Badge
                    variant={section.state === "완료" ? "default" : section.state === "미비" ? "secondary" : "outline"}
                    className="text-[10px] px-1.5"
                  >
                    {section.state}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {section.evidence_count}건
                    {section.has_stats && " + 통계"}
                    {section.has_standards && " + 기준비교"}
                  </span>
                </div>
              );
            })}

            {/* 부록 */}
            <div className="mt-2 border-t pt-2 space-y-1.5">
              <div className="flex items-center gap-2 py-1 pl-2">
                <Database className="h-3.5 w-3.5 text-muted-foreground" />
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={options.include_appendix_a}
                    onChange={(e) =>
                      onOptionsChange({ ...options, include_appendix_a: e.target.checked })
                    }
                    className="h-3.5 w-3.5 rounded border-gray-300"
                  />
                  <span>부록 A: 상세 측정 데이터</span>
                </label>
              </div>

              <div className="flex items-center gap-2 py-1 pl-2">
                <GitCompare className="h-3.5 w-3.5 text-muted-foreground" />
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={options.include_appendix_b}
                    onChange={(e) =>
                      onOptionsChange({ ...options, include_appendix_b: e.target.checked })
                    }
                    className="h-3.5 w-3.5 rounded border-gray-300"
                  />
                  <span>부록 B: 유사사례 매칭 결과</span>
                  <span className="text-xs text-muted-foreground">
                    ({preview.similar_case_count}건)
                  </span>
                </label>
              </div>

              <div className="flex items-center gap-2 py-1 pl-2">
                <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={options.include_appendix_c}
                    onChange={(e) =>
                      onOptionsChange({ ...options, include_appendix_c: e.target.checked })
                    }
                    className="h-3.5 w-3.5 rounded border-gray-300"
                  />
                  <span>부록 C: QA 검사 결과</span>
                  <span className="text-xs text-muted-foreground">
                    ({preview.qa_issue_count}건)
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
