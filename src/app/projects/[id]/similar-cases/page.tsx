"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { SimilarCaseMatch } from "@/types/similar-case";
import { matchSimilarCases } from "@/lib/similar-case-api";
import { SimilarCaseMatchTable } from "@/components/similar-case/similar-case-match-table";
import { SimilarCaseDetailSheet } from "@/components/similar-case/similar-case-detail-sheet";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Search } from "lucide-react";

export default function SimilarCasesPage() {
  const params = useParams();
  const projectId = params.id as string;

  // ─── 상태 ───
  const [matches, setMatches] = useState<SimilarCaseMatch[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 상세 시트
  const [detailMatch, setDetailMatch] = useState<SimilarCaseMatch | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // ─── 데이터 로딩 ───
  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const result = await matchSimilarCases(projectId, { top_k: 20 });
      setMatches(result.matches);
      setTotal(result.total);
    } catch (err) {
      console.error("유사사례 매칭 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchMatches();
  }, [fetchMatches]);

  // ─── 핸들러 ───
  const handleView = (match: SimilarCaseMatch) => {
    setDetailMatch(match);
    setDetailOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}/evidences`}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">유사사례 매칭</h2>
            <p className="text-sm text-muted-foreground">
              프로젝트와 유사한 과거 환경영향평가 사례를 검색합니다.
            </p>
          </div>
        </div>
        <Button onClick={fetchMatches} disabled={loading}>
          <Search className="mr-2 h-4 w-4" />
          다시 검색
        </Button>
      </div>

      {/* 통계 카드 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">매칭 결과</CardTitle>
            <span className="text-sm text-muted-foreground">
              {total}건의 유사사례
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            사업 유형(35%), 위치(25%), 규모(20%), 환경 분야(20%) 가중 평균으로
            유사도를 산출합니다.
          </p>
        </CardContent>
      </Card>

      {/* 매칭 결과 테이블 */}
      <SimilarCaseMatchTable
        matches={matches}
        loading={loading}
        onView={handleView}
      />

      {/* 상세 시트 */}
      <SimilarCaseDetailSheet
        match={detailMatch}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
