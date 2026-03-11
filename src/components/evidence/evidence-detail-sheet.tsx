"use client";

import { useEffect, useState } from "react";
import type { Evidence, SourceSnapshot } from "@/types/evidence";
import { EVIDENCE_CATEGORIES } from "@/types/evidence";
import { getSnapshot } from "@/lib/evidence-api";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface EvidenceDetailSheetProps {
  evidence: Evidence | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** 레이블-값 쌍 표시 */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-2 py-1.5">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <span className="text-sm break-all">{children}</span>
    </div>
  );
}

export function EvidenceDetailSheet({
  evidence,
  open,
  onOpenChange,
}: EvidenceDetailSheetProps) {
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  // 스냅샷 ID가 있으면 raw_payload 조회
  useEffect(() => {
    if (!evidence?.snapshot_id) {
      setSnapshot(null);
      return;
    }
    setSnapshotLoading(true);
    getSnapshot(evidence.snapshot_id)
      .then(setSnapshot)
      .catch(() => setSnapshot(null))
      .finally(() => setSnapshotLoading(false));
  }, [evidence?.snapshot_id]);

  if (!evidence) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[480px] overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="text-lg">증거 상세</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-1">
          <Field label="분야">
            <Badge variant="outline">
              {EVIDENCE_CATEGORIES[evidence.category] ?? evidence.category}
            </Badge>
          </Field>
          <Field label="지표">{evidence.indicator}</Field>
          <Field label="측정값">{evidence.value}</Field>
          {evidence.numeric_value !== null && (
            <Field label="수치값">{evidence.numeric_value}</Field>
          )}
          <Field label="단위">{evidence.unit ?? "—"}</Field>
          <Field label="관측 시점">
            {evidence.observed_at
              ? new Date(evidence.observed_at).toLocaleString("ko-KR")
              : "—"}
          </Field>
          <Field label="구분">
            {evidence.screening_only ? (
              <Badge variant="secondary">스크리닝</Badge>
            ) : (
              <Badge className="bg-primary/10 text-primary hover:bg-primary/20">
                본평가
              </Badge>
            )}
          </Field>
          {evidence.location && (
            <Field label="위치 (경도, 위도)">
              {evidence.location.coordinates.join(", ")}
            </Field>
          )}
          <Field label="등록일">
            {new Date(evidence.created_at).toLocaleString("ko-KR")}
          </Field>
        </div>

        {/* 메타데이터 */}
        {evidence.metadata_json &&
          Object.keys(evidence.metadata_json).length > 0 && (
            <>
              <Separator className="my-4" />
              <h4 className="mb-2 text-sm font-semibold">메타데이터</h4>
              <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
                {JSON.stringify(evidence.metadata_json, null, 2)}
              </pre>
            </>
          )}

        {/* Raw Payload (스냅샷) */}
        {evidence.snapshot_id && (
          <>
            <Separator className="my-4" />
            <h4 className="mb-2 text-sm font-semibold">
              원시 데이터 (Raw Payload)
            </h4>
            {snapshotLoading ? (
              <p className="text-sm text-muted-foreground">불러오는 중…</p>
            ) : snapshot ? (
              <>
                <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>상태: {snapshot.status}</span>
                  <span>·</span>
                  <span>
                    수집: {new Date(snapshot.fetched_at).toLocaleString("ko-KR")}
                  </span>
                </div>
                <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(snapshot.raw_payload, null, 2)}
                </pre>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                스냅샷을 불러올 수 없습니다.
              </p>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
