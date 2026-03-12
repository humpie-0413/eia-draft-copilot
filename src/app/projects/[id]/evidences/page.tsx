"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type {
  Evidence,
  EvidenceCategory,
  EvidenceFormData,
} from "@/types/evidence";
import {
  listEvidences,
  createEvidence,
  updateEvidence,
  deleteEvidence,
} from "@/lib/evidence-api";
import { EvidenceFilters } from "@/components/evidence/evidence-filters";
import { EvidenceTable } from "@/components/evidence/evidence-table";
import { EvidenceDetailSheet } from "@/components/evidence/evidence-detail-sheet";
import { EvidenceFormDialog } from "@/components/evidence/evidence-form-dialog";
import { CollectDataDialog } from "@/components/evidence/collect-data-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, ArrowLeft, Download } from "lucide-react";
import Link from "next/link";

export default function EvidenceWorkbenchPage() {
  const params = useParams();
  const projectId = params.id as string;

  // ─── 상태 ───
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // 필터
  const [category, setCategory] = useState<EvidenceCategory | undefined>();
  const [screeningOnly, setScreeningOnly] = useState<boolean | undefined>();

  // 상세 시트
  const [detailEvidence, setDetailEvidence] = useState<Evidence | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // 추가/편집 다이얼로그
  const [formEvidence, setFormEvidence] = useState<Evidence | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  // 삭제 확인
  const [deleteTarget, setDeleteTarget] = useState<Evidence | null>(null);

  // 데이터 수집 다이얼로그
  const [collectOpen, setCollectOpen] = useState(false);

  // ─── 데이터 로딩 ───
  const fetchEvidences = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listEvidences(
        projectId,
        { category, screening_only: screeningOnly },
        { limit: 100 },
      );
      setEvidences(result.items);
      setTotal(result.total);
    } catch (err) {
      console.error("증거 목록 조회 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, category, screeningOnly]);

  useEffect(() => {
    fetchEvidences();
  }, [fetchEvidences]);

  // ─── 핸들러 ───
  const handleView = (ev: Evidence) => {
    setDetailEvidence(ev);
    setDetailOpen(true);
  };

  const handleEdit = (ev: Evidence) => {
    setFormEvidence(ev);
    setFormOpen(true);
  };

  const handleCreate = () => {
    setFormEvidence(null);
    setFormOpen(true);
  };

  const handleDelete = async (ev: Evidence) => {
    setDeleteTarget(ev);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteEvidence(deleteTarget.id);
      setDeleteTarget(null);
      await fetchEvidences();
    } catch (err) {
      console.error("증거 삭제 실패:", err);
    }
  };

  const handleFormSubmit = async (data: EvidenceFormData) => {
    // 폼 데이터를 API 요청 형식으로 변환
    const payload: Record<string, unknown> = {
      category: data.category,
      indicator: data.indicator,
      value: data.value,
      numeric_value: data.numeric_value,
      unit: data.unit,
      observed_at: data.observed_at ? new Date(data.observed_at).toISOString() : null,
      screening_only: data.screening_only,
      metadata_json: data.metadata_json.trim()
        ? JSON.parse(data.metadata_json)
        : null,
    };

    if (formEvidence) {
      // 수정
      await updateEvidence(formEvidence.id, payload);
    } else {
      // 생성
      payload.project_id = projectId;
      await createEvidence(payload);
    }

    await fetchEvidences();
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">증거 작업대</h2>
            <p className="text-sm text-muted-foreground">
              프로젝트 증거 데이터를 조회, 추가, 편집할 수 있습니다.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setCollectOpen(true)}>
            <Download className="mr-2 h-4 w-4" />
            데이터 수집
          </Button>
          <Button onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            증거 추가
          </Button>
        </div>
      </div>

      {/* 필터 + 통계 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">필터</CardTitle>
            <span className="text-sm text-muted-foreground">
              총 {total}건
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <EvidenceFilters
            category={category}
            screeningOnly={screeningOnly}
            onCategoryChange={setCategory}
            onScreeningOnlyChange={setScreeningOnly}
          />
        </CardContent>
      </Card>

      {/* 증거 테이블 */}
      <EvidenceTable
        evidences={evidences}
        loading={loading}
        onView={handleView}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      {/* 상세 시트 */}
      <EvidenceDetailSheet
        evidence={detailEvidence}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />

      {/* 추가/편집 다이얼로그 */}
      <EvidenceFormDialog
        evidence={formEvidence}
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleFormSubmit}
      />

      {/* 데이터 수집 다이얼로그 */}
      <CollectDataDialog
        projectId={projectId}
        open={collectOpen}
        onOpenChange={setCollectOpen}
        onComplete={fetchEvidences}
      />

      {/* 삭제 확인 다이얼로그 */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-sm rounded-lg bg-background p-6 shadow-lg">
            <h3 className="mb-2 text-lg font-semibold">증거 삭제</h3>
            <p className="mb-4 text-sm text-muted-foreground">
              &quot;{deleteTarget.indicator}&quot; 증거를 삭제하시겠습니까? 이
              작업은 되돌릴 수 없습니다.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
              >
                취소
              </Button>
              <Button variant="destructive" onClick={confirmDelete}>
                삭제
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
