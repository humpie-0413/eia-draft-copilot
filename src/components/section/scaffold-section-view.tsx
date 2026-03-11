"use client";

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

interface ScaffoldSectionViewProps {
  section: ScaffoldSection;
}

export function ScaffoldSectionView({ section }: ScaffoldSectionViewProps) {
  const hasEntries = section.evidence_entries.length > 0;

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
        {/* 근거 요약문 (evidence 기반) */}
        {hasEntries && (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="mb-1 text-xs font-medium text-muted-foreground">
              근거 요약 (evidence 기반 자동 생성)
            </p>
            <pre className="whitespace-pre-wrap text-sm leading-relaxed">
              {section.summary_text}
            </pre>
          </div>
        )}

        {/* 근거 항목 테이블 */}
        {hasEntries ? (
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
                    {entry.observed_at ? entry.observed_at.slice(0, 10) : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">
            이 섹션에 배치할 증거 데이터가 없습니다.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
