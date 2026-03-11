"use client";

import type { SimilarCaseMatch } from "@/types/similar-case";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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

/** 유사도 점수 바 */
function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className="h-2 rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

interface SimilarCaseDetailSheetProps {
  match: SimilarCaseMatch | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SimilarCaseDetailSheet({
  match,
  open,
  onOpenChange,
}: SimilarCaseDetailSheetProps) {
  if (!match) return null;

  const c = match.similar_case;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[420px] sm:w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-lg">{c.name}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* 유사도 점수 */}
          <div>
            <h4 className="mb-3 text-sm font-semibold">유사도 점수</h4>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-2xl font-bold tabular-nums">
                {Math.round(match.overall_score * 100)}%
              </span>
              <span className="text-sm text-muted-foreground">종합 유사도</span>
            </div>
            <div className="space-y-3">
              <ScoreBar label="사업 유형" score={match.type_score} />
              <ScoreBar label="위치" score={match.location_score} />
              <ScoreBar label="규모" score={match.scale_score} />
              <ScoreBar label="환경 분야" score={match.category_score} />
            </div>
          </div>

          <Separator />

          {/* 기본 정보 */}
          <div>
            <h4 className="mb-3 text-sm font-semibold">기본 정보</h4>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">사업 유형</dt>
                <dd>
                  <Badge variant="outline">
                    {PROJECT_TYPE_LABELS[c.project_type] ?? c.project_type}
                  </Badge>
                </dd>
              </div>
              {c.area_sqm != null && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">사업 면적</dt>
                  <dd>{c.area_sqm.toLocaleString()} m²</dd>
                </div>
              )}
              {c.completed_at && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">평가 완료</dt>
                  <dd>{new Date(c.completed_at).toLocaleDateString("ko-KR")}</dd>
                </div>
              )}
              {c.source_url && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">원본 문서</dt>
                  <dd>
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      링크
                    </a>
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* 환경 분야 */}
          {c.evidence_categories && c.evidence_categories.length > 0 && (
            <>
              <Separator />
              <div>
                <h4 className="mb-3 text-sm font-semibold">환경 분야</h4>
                <div className="flex flex-wrap gap-1.5">
                  {c.evidence_categories.map((cat) => (
                    <Badge key={cat} variant="secondary">
                      {EVIDENCE_CATEGORIES[
                        cat as keyof typeof EVIDENCE_CATEGORIES
                      ] ?? cat}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* 설명 */}
          {c.description && (
            <>
              <Separator />
              <div>
                <h4 className="mb-2 text-sm font-semibold">설명</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {c.description}
                </p>
              </div>
            </>
          )}

          {/* 요약 */}
          {c.summary && (
            <>
              <Separator />
              <div>
                <h4 className="mb-2 text-sm font-semibold">평가서 요약</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {c.summary}
                </p>
              </div>
            </>
          )}

          {/* 주요 발견사항 */}
          {c.key_findings && Object.keys(c.key_findings).length > 0 && (
            <>
              <Separator />
              <div>
                <h4 className="mb-2 text-sm font-semibold">주요 발견사항</h4>
                <pre className="rounded bg-muted p-3 text-xs overflow-x-auto">
                  {JSON.stringify(c.key_findings, null, 2)}
                </pre>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
