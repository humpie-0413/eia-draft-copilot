"use client";

import type { Evidence } from "@/types/evidence";
import { EVIDENCE_CATEGORIES } from "@/types/evidence";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, Pencil, Trash2 } from "lucide-react";

interface EvidenceTableProps {
  evidences: Evidence[];
  loading: boolean;
  onView: (evidence: Evidence) => void;
  onEdit: (evidence: Evidence) => void;
  onDelete: (evidence: Evidence) => void;
}

/** 날짜 포맷 (YYYY-MM-DD HH:mm) */
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function EvidenceTable({
  evidences,
  loading,
  onView,
  onEdit,
  onDelete,
}: EvidenceTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground">
        불러오는 중…
      </div>
    );
  }

  if (evidences.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <p>등록된 증거가 없습니다.</p>
        <p className="text-sm">위의 &quot;증거 추가&quot; 버튼으로 새 증거를 등록하세요.</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">분야</TableHead>
            <TableHead>지표</TableHead>
            <TableHead>측정값</TableHead>
            <TableHead className="w-[70px]">단위</TableHead>
            <TableHead className="w-[100px]">관측일</TableHead>
            <TableHead className="w-[80px]">구분</TableHead>
            <TableHead className="w-[120px] text-right">작업</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {evidences.map((ev) => (
            <TableRow key={ev.id}>
              <TableCell>
                <Badge variant="outline" className="text-xs">
                  {EVIDENCE_CATEGORIES[ev.category] ?? ev.category}
                </Badge>
              </TableCell>
              <TableCell className="font-medium">{ev.indicator}</TableCell>
              <TableCell>
                {ev.numeric_value !== null ? ev.numeric_value : ev.value}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {ev.unit ?? "—"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(ev.observed_at)}
              </TableCell>
              <TableCell>
                {ev.screening_only ? (
                  <Badge variant="secondary" className="text-xs">
                    스크리닝
                  </Badge>
                ) : (
                  <Badge className="bg-primary/10 text-primary text-xs hover:bg-primary/20">
                    본평가
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title="상세 보기"
                    onClick={() => onView(ev)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title="수정"
                    onClick={() => onEdit(ev)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    title="삭제"
                    onClick={() => onDelete(ev)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
