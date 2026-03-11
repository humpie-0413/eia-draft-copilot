"use client";

import type { SimilarCaseMatch } from "@/types/similar-case";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Eye } from "lucide-react";
import { EVIDENCE_CATEGORIES } from "@/types/evidence";

const PROJECT_TYPE_LABELS: Record<string, string> = {
  road: "도로",
  railway: "철도",
  power_plant: "발전소",
  industrial: "산업단지",
  housing: "주택단지",
  airport: "공항",
  port: "항만",
  dam: "댐",
  reclamation: "매립",
  other: "기타",
};

/** 유사도 점수에 따른 색상 배지 */
function ScoreBadge({ score, label }: { score: number; label?: string }) {
  let variant: "default" | "secondary" | "outline" | "destructive" = "outline";
  if (score >= 0.7) variant = "default";
  else if (score >= 0.4) variant = "secondary";

  return (
    <Badge variant={variant} className="font-mono text-xs tabular-nums">
      {label ? `${label} ` : ""}
      {(score * 100).toFixed(0)}%
    </Badge>
  );
}

interface SimilarCaseMatchTableProps {
  matches: SimilarCaseMatch[];
  loading: boolean;
  onView: (match: SimilarCaseMatch) => void;
}

export function SimilarCaseMatchTable({
  matches,
  loading,
  onView,
}: SimilarCaseMatchTableProps) {
  if (loading) {
    return (
      <p className="py-16 text-center text-muted-foreground">
        유사사례를 검색하는 중...
      </p>
    );
  }

  if (matches.length === 0) {
    return (
      <p className="py-16 text-center text-muted-foreground">
        매칭되는 유사사례가 없습니다.
      </p>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px]">#</TableHead>
            <TableHead>사례명</TableHead>
            <TableHead>사업 유형</TableHead>
            <TableHead>환경 분야</TableHead>
            <TableHead className="text-center">종합 유사도</TableHead>
            <TableHead className="text-center">유형</TableHead>
            <TableHead className="text-center">위치</TableHead>
            <TableHead className="text-center">규모</TableHead>
            <TableHead className="text-center">분야</TableHead>
            <TableHead className="w-[60px]" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {matches.map((match, idx) => {
            const c = match.similar_case;
            return (
              <TableRow key={c.id}>
                <TableCell className="text-muted-foreground">
                  {idx + 1}
                </TableCell>
                <TableCell className="font-medium max-w-[200px] truncate">
                  {c.name}
                </TableCell>
                <TableCell>
                  <Badge variant="outline">
                    {PROJECT_TYPE_LABELS[c.project_type] ?? c.project_type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {(c.evidence_categories ?? []).slice(0, 3).map((cat) => (
                      <Badge
                        key={cat}
                        variant="secondary"
                        className="text-xs"
                      >
                        {EVIDENCE_CATEGORIES[
                          cat as keyof typeof EVIDENCE_CATEGORIES
                        ] ?? cat}
                      </Badge>
                    ))}
                    {(c.evidence_categories ?? []).length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{(c.evidence_categories ?? []).length - 3}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <ScoreBadge score={match.overall_score} />
                </TableCell>
                <TableCell className="text-center">
                  <ScoreBadge score={match.type_score} />
                </TableCell>
                <TableCell className="text-center">
                  <ScoreBadge score={match.location_score} />
                </TableCell>
                <TableCell className="text-center">
                  <ScoreBadge score={match.scale_score} />
                </TableCell>
                <TableCell className="text-center">
                  <ScoreBadge score={match.category_score} />
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => onView(match)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
