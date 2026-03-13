"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { SectionStatus } from "@/types/section";
import { getSectionsStatus } from "@/lib/section-api";
import { SectionStatusCard } from "@/components/section/section-status-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, FileText } from "lucide-react";

export default function SectionPlannerPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [sections, setSections] = useState<SectionStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getSectionsStatus(projectId);
      setSections(result.sections);
    } catch (err) {
      console.error("섹션 상태 조회 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // 전체 통계
  const totalEvidence = sections.reduce(
    (sum, s) => sum + s.total_evidence_count,
    0,
  );
  const completeSections = sections.filter(
    (s) => s.status === "complete" || s.status === "auto_filled",
  ).length;
  const partialSections = sections.filter(
    (s) => s.status === "partial",
  ).length;

  // 평가 범위 통계
  const requiredSections = sections.filter((s) => s.scope === "required");
  const requiredCount = requiredSections.length;
  const requiredFulfilled = requiredSections.filter(
    (s) => s.status === "complete" || s.status === "auto_filled",
  ).length;
  const hasScope = sections.some((s) => s.scope !== "");

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/projects">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              섹션 플래너
            </h2>
            <p className="text-sm text-muted-foreground">
              환경영향평가서 섹션별 증거 충족 현황을 확인합니다.
            </p>
          </div>
        </div>
        <Link href={`/projects/${projectId}/draft`}>
          <Button>
            <FileText className="mr-2 h-4 w-4" />
            초안 뼈대 보기
          </Button>
        </Link>
      </div>

      {/* 평가 범위 안내 (사업유형 설정 시) */}
      {hasScope && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="py-3">
            <div className="flex items-center gap-4 text-sm">
              <span className="font-medium">평가 범위</span>
              <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                필수 {requiredFulfilled}/{requiredCount}
              </Badge>
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                권장 {sections.filter((s) => s.scope === "recommended").length}
              </Badge>
              <Badge variant="outline" className="bg-gray-50 text-gray-500 border-gray-200">
                선택 {sections.filter((s) => s.scope === "optional").length}
              </Badge>
              {requiredCount > 0 && requiredFulfilled < requiredCount && (
                <span className="text-xs text-red-600">
                  필수 섹션 {requiredCount - requiredFulfilled}건 미충족
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 요약 통계 */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">
              전체 섹션
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{sections.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">
              충족
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">
              {completeSections}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">
              일부 충족
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-yellow-600">
              {partialSections}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">
              {hasScope ? "전문가 필요" : "미수집"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">
              {sections.filter((s) => s.status === "expert_required").length ||
                sections.filter((s) => s.status === "empty").length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 전체 증거 수 */}
      <p className="text-sm text-muted-foreground">
        본 평가 증거 데이터 총 {totalEvidence}건
      </p>

      {/* 섹션 상태 카드 그리드 */}
      {loading ? (
        <p className="py-16 text-center text-muted-foreground">
          불러오는 중…
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => (
            <Link
              key={section.section_key}
              href={`/projects/${projectId}/draft?section=${section.section_key}`}
            >
              <SectionStatusCard section={section} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
