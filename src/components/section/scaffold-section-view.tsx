"use client";

import { useState } from "react";
import type { ScaffoldSection } from "@/types/section";
import type { EnhanceResponse } from "@/types/llm";
import { enhanceSectionNarrative } from "@/lib/llm-api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, Sparkles, RotateCcw } from "lucide-react";

interface ScaffoldSectionViewProps {
  section: ScaffoldSection;
  projectId?: string;
}

export function ScaffoldSectionView({ section, projectId }: ScaffoldSectionViewProps) {
  const hasEntries = section.evidence_entries.length > 0;
  const [showRawData, setShowRawData] = useState(false);

  // LLM 보강 상태
  const [enhanceResult, setEnhanceResult] = useState<EnhanceResponse | null>(null);
  const [enhancing, setEnhancing] = useState(false);
  const [showComparison, setShowComparison] = useState(false);

  const handleEnhance = async () => {
    if (!projectId) return;
    setEnhancing(true);
    try {
      const result = await enhanceSectionNarrative(projectId, section.section_key);
      setEnhanceResult(result);
      setShowComparison(true);
    } catch (err) {
      console.error("서술문 보강 실패:", err);
    } finally {
      setEnhancing(false);
    }
  };

  const handleReset = () => {
    setEnhanceResult(null);
    setShowComparison(false);
  };

  // 현재 표시할 서술문 결정
  const displayNarrative = enhanceResult && !enhanceResult.is_fallback
    ? enhanceResult.enhanced_narrative
    : section.narrative;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{section.title}</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {section.description}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* AI 문체 보강 버튼 */}
            {projectId && section.narrative && hasEntries && (
              enhanceResult && !enhanceResult.is_fallback ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 text-xs"
                  onClick={handleReset}
                >
                  <RotateCcw className="h-3 w-3" />
                  원본 복원
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 text-xs"
                  onClick={handleEnhance}
                  disabled={enhancing}
                >
                  <Sparkles className="h-3 w-3" />
                  {enhancing ? "보강 중…" : "AI 문체 보강"}
                </Button>
              )
            )}
            <Badge variant="outline" className="text-xs">
              근거 {section.evidence_entries.length}건
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 보강 전/후 비교 모드 */}
        {showComparison && enhanceResult && !enhanceResult.is_fallback ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[10px]">
                {enhanceResult.adapter_used}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] text-muted-foreground"
                onClick={() => setShowComparison(false)}
              >
                비교 닫기
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {/* 원본 */}
              <div className="rounded-md border border-muted bg-muted/20 p-3">
                <p className="mb-1 text-[10px] font-medium text-muted-foreground">
                  원본 (템플릿)
                </p>
                <div className="space-y-1.5 text-sm leading-relaxed text-muted-foreground">
                  {enhanceResult.original_narrative.split("\n").map((line, i) =>
                    line.trim() ? <p key={i}>{line}</p> : null,
                  )}
                </div>
              </div>
              {/* 보강 */}
              <div className="rounded-md border-l-4 border-primary/30 bg-primary/5 p-3">
                <p className="mb-1 text-[10px] font-medium text-primary/70">
                  AI 보강
                </p>
                <div className="space-y-1.5 text-sm leading-relaxed">
                  {enhanceResult.enhanced_narrative.split("\n").map((line, i) =>
                    line.trim() ? <p key={i}>{line}</p> : null,
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* 서술문 미리보기 (기본 또는 보강 결과) */
          displayNarrative && (
            <div className="rounded-md border-l-4 border-primary/30 bg-primary/5 p-4">
              <div className="mb-1 flex items-center gap-2">
                <p className="text-xs font-medium text-primary/70">
                  현황 및 영향 분석
                </p>
                {enhanceResult && !enhanceResult.is_fallback && (
                  <Badge variant="secondary" className="text-[10px]">
                    AI 보강
                  </Badge>
                )}
              </div>
              <div className="space-y-1.5 text-sm leading-relaxed">
                {displayNarrative.split("\n").map((line, i) =>
                  line.trim() ? (
                    <p key={i}>{line}</p>
                  ) : null,
                )}
              </div>
            </div>
          )
        )}

        {/* 통계 요약 및 기준 비교 (summary_text) */}
        {hasEntries && section.summary_text && (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium text-muted-foreground">
              측정 현황 요약
            </p>
            <pre className="whitespace-pre-wrap text-sm leading-relaxed">
              {section.summary_text}
            </pre>
          </div>
        )}

        {/* 근거 항목 테이블 (접을 수 있는 영역) */}
        {hasEntries ? (
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="mb-2 h-7 px-2 text-xs text-muted-foreground"
              onClick={() => setShowRawData(!showRawData)}
            >
              {showRawData ? (
                <ChevronDown className="mr-1 h-3 w-3" />
              ) : (
                <ChevronRight className="mr-1 h-3 w-3" />
              )}
              원시 데이터 ({section.evidence_entries.length}건)
            </Button>
            {showRawData && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[160px]">지표</TableHead>
                    <TableHead>측정값</TableHead>
                    <TableHead className="w-[80px]">단위</TableHead>
                    <TableHead className="w-[110px]">관측일</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {section.evidence_entries.map((entry) => (
                    <TableRow key={entry.evidence_id}>
                      <TableCell className="font-medium text-sm">
                        {entry.indicator}
                      </TableCell>
                      <TableCell className="text-sm">
                        {entry.value}
                        {entry.numeric_value !== null && (
                          <span className="ml-1 text-muted-foreground">
                            ({entry.numeric_value})
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {entry.unit ?? "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {entry.observed_at
                          ? entry.observed_at.slice(0, 10)
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {section.narrative ||
              "이 섹션에 배치할 증거 데이터가 없습니다."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
