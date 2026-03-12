"use client";

import { useState } from "react";
import type { ScaffoldSection } from "@/types/section";
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
import { ChevronDown, ChevronRight } from "lucide-react";

interface ScaffoldSectionViewProps {
  section: ScaffoldSection;
}

export function ScaffoldSectionView({ section }: ScaffoldSectionViewProps) {
  const hasEntries = section.evidence_entries.length > 0;
  const [showRawData, setShowRawData] = useState(false);

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
          <Badge variant="outline" className="text-xs">
            근거 {section.evidence_entries.length}건
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 서술문 미리보기 (Post-3 신규) */}
        {section.narrative && (
          <div className="rounded-md border-l-4 border-primary/30 bg-primary/5 p-4">
            <p className="mb-1 text-xs font-medium text-primary/70">
              현황 및 영향 분석
            </p>
            <div className="space-y-1.5 text-sm leading-relaxed">
              {section.narrative.split("\n").map((line, i) =>
                line.trim() ? (
                  <p key={i}>{line}</p>
                ) : null,
              )}
            </div>
          </div>
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
