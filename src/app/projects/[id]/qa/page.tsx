"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { QaResult, QaSeverity } from "@/types/qa";
import { getQaResult } from "@/lib/qa-api";
import { QaIssueList } from "@/components/qa/qa-issue-list";
import { QaSummaryBar } from "@/components/qa/qa-summary-bar";
import { ExportButton } from "@/components/qa/export-button";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  FileText,
  RefreshCw,
  Loader2,
} from "lucide-react";

const SEVERITY_TABS: { value: QaSeverity | "all"; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "critical", label: "심각" },
  { value: "warning", label: "경고" },
  { value: "info", label: "참고" },
];

export default function QaPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [qaResult, setQaResult] = useState<QaResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<QaSeverity | "all">("all");

  const fetchQa = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getQaResult(projectId);
      setQaResult(result);
    } catch (err) {
      console.error("QA 결과 조회 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchQa();
  }, [fetchQa]);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              QA 검사 결과
            </h2>
            <p className="text-sm text-muted-foreground">
              환경영향평가서 품질 검사 — 필수 증거 누락 및 규정 준수 확인
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchQa}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            재검사
          </Button>
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="outline" size="sm">
              <FileText className="mr-2 h-4 w-4" />
              초안 뼈대
            </Button>
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="py-16 text-center text-muted-foreground">
          QA 검사를 실행하는 중…
        </p>
      ) : qaResult ? (
        <>
          {/* 요약 바 */}
          <QaSummaryBar
            summary={qaResult.summary}
            exportReady={qaResult.export_ready}
          />

          {/* Export 버튼 */}
          <ExportButton
            projectId={projectId}
            exportReady={qaResult.export_ready}
            criticalCount={qaResult.summary.critical_count}
          />

          {/* 심각도 필터 탭 */}
          <div className="flex gap-2">
            {SEVERITY_TABS.map((tab) => {
              const count =
                tab.value === "all"
                  ? qaResult.summary.total
                  : tab.value === "critical"
                    ? qaResult.summary.critical_count
                    : tab.value === "warning"
                      ? qaResult.summary.warning_count
                      : qaResult.summary.info_count;

              return (
                <button
                  key={tab.value}
                  onClick={() => setActiveTab(tab.value)}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                    activeTab === tab.value
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {tab.label}
                  <Badge
                    variant="secondary"
                    className={`text-[10px] px-1.5 ${
                      activeTab === tab.value
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : ""
                    }`}
                  >
                    {count}
                  </Badge>
                </button>
              );
            })}
          </div>

          {/* 이슈 목록 */}
          <QaIssueList
            issues={qaResult.issues}
            filterSeverity={activeTab === "all" ? null : activeTab}
          />
        </>
      ) : (
        <p className="py-16 text-center text-muted-foreground">
          QA 결과를 불러올 수 없습니다.
        </p>
      )}
    </div>
  );
}
