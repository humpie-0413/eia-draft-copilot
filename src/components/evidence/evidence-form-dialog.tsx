"use client";

import { useEffect, useState } from "react";
import type { Evidence, EvidenceCategory, EvidenceFormData } from "@/types/evidence";
import { EVIDENCE_CATEGORIES } from "@/types/evidence";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface EvidenceFormDialogProps {
  /** null이면 생성 모드, Evidence 객체면 편집 모드 */
  evidence: Evidence | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: EvidenceFormData) => Promise<void>;
}

const EMPTY_FORM: EvidenceFormData = {
  category: "air_quality",
  indicator: "",
  value: "",
  numeric_value: null,
  unit: null,
  observed_at: null,
  screening_only: false,
  metadata_json: "",
};

function evidenceToForm(ev: Evidence): EvidenceFormData {
  return {
    category: ev.category,
    indicator: ev.indicator,
    value: ev.value,
    numeric_value: ev.numeric_value,
    unit: ev.unit,
    observed_at: ev.observed_at ? ev.observed_at.slice(0, 16) : null,
    screening_only: ev.screening_only,
    metadata_json: ev.metadata_json
      ? JSON.stringify(ev.metadata_json, null, 2)
      : "",
  };
}

export function EvidenceFormDialog({
  evidence,
  open,
  onOpenChange,
  onSubmit,
}: EvidenceFormDialogProps) {
  const isEdit = evidence !== null;
  const [form, setForm] = useState<EvidenceFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm(evidence ? evidenceToForm(evidence) : EMPTY_FORM);
      setError(null);
    }
  }, [open, evidence]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // 기본 유효성 검사
    if (!form.indicator.trim()) {
      setError("지표명을 입력하세요.");
      return;
    }
    if (!form.value.trim()) {
      setError("측정값을 입력하세요.");
      return;
    }

    // 메타데이터 JSON 파싱 검증
    if (form.metadata_json.trim()) {
      try {
        JSON.parse(form.metadata_json);
      } catch {
        setError("메타데이터가 올바른 JSON 형식이 아닙니다.");
        return;
      }
    }

    setSubmitting(true);
    try {
      await onSubmit(form);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "증거 수정" : "증거 추가"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 분야 */}
          <div className="space-y-1.5">
            <Label>분야 *</Label>
            <Select
              value={form.category}
              onValueChange={(v) =>
                setForm((f) => ({ ...f, category: v as EvidenceCategory }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(EVIDENCE_CATEGORIES).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 지표명 */}
          <div className="space-y-1.5">
            <Label>지표명 *</Label>
            <Input
              value={form.indicator}
              onChange={(e) =>
                setForm((f) => ({ ...f, indicator: e.target.value }))
              }
              placeholder="예: PM10, BOD, 소음도"
              maxLength={200}
            />
          </div>

          {/* 측정값 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>측정값 *</Label>
              <Input
                value={form.value}
                onChange={(e) =>
                  setForm((f) => ({ ...f, value: e.target.value }))
                }
                placeholder="예: 45"
                maxLength={255}
              />
            </div>
            <div className="space-y-1.5">
              <Label>수치값</Label>
              <Input
                type="number"
                step="any"
                value={form.numeric_value ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    numeric_value: e.target.value
                      ? parseFloat(e.target.value)
                      : null,
                  }))
                }
                placeholder="수치 (선택)"
              />
            </div>
          </div>

          {/* 단위 + 관측일 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>단위</Label>
              <Input
                value={form.unit ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    unit: e.target.value || null,
                  }))
                }
                placeholder="예: μg/m³, mg/L"
                maxLength={50}
              />
            </div>
            <div className="space-y-1.5">
              <Label>관측일시</Label>
              <Input
                type="datetime-local"
                value={form.observed_at ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    observed_at: e.target.value || null,
                  }))
                }
              />
            </div>
          </div>

          {/* 스크리닝 전용 */}
          <div className="flex items-center gap-2">
            <Switch
              id="form-screening"
              checked={form.screening_only}
              onCheckedChange={(checked) =>
                setForm((f) => ({ ...f, screening_only: checked }))
              }
            />
            <Label htmlFor="form-screening" className="cursor-pointer">
              스크리닝 전용 데이터
            </Label>
          </div>

          {/* 메타데이터 JSON */}
          <div className="space-y-1.5">
            <Label>추가 메타데이터 (JSON)</Label>
            <Textarea
              value={form.metadata_json}
              onChange={(e) =>
                setForm((f) => ({ ...f, metadata_json: e.target.value }))
              }
              placeholder='{"source": "현장조사", "note": "..."}'
              rows={3}
              className="font-mono text-xs"
            />
          </div>

          {/* 에러 메시지 */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              취소
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "저장 중…" : isEdit ? "수정" : "추가"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
