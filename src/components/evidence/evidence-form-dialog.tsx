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

/**
 * 수동 입력 섹션별 권장 지표 목록.
 * 공공데이터 커넥터가 없는 5개 분야에 대해 필수 지표를 안내한다.
 */
const RECOMMENDED_INDICATORS: Partial<
  Record<EvidenceCategory, { indicators: string[]; hint: string }>
> = {
  land_use: {
    indicators: ["용도지역", "토지피복", "개발면적"],
    hint: "국토이용정보 또는 토지이용현황도에서 확인",
  },
  traffic: {
    indicators: ["교통량_현황", "서비스수준"],
    hint: "교통영향평가 보고서 또는 도로교통량 통계자료 참조",
  },
  waste: {
    indicators: ["폐기물_발생량", "폐기물_종류"],
    hint: "폐기물 관리법 기준, 사업장 폐기물 발생량 조사 자료",
  },
  landscape: {
    indicators: ["주요_조망점", "경관_유형"],
    hint: "경관영향 검토서 또는 현장조사 사진 자료",
  },
  cultural_heritage: {
    indicators: ["문화재_목록", "이격거리"],
    hint: "문화재청 문화재 검색 또는 현장 실측 자료",
  },
  soil: {
    indicators: ["Cd", "Cu", "Pb", "Zn", "Ni", "Cr6+", "pH", "유기물함량"],
    hint: "토양측정망 커넥터 자동 수집 가능. 수동 시 토양오염 조사 결과 참조",
  },
  climate: {
    indicators: ["평균기온", "최고기온", "최저기온", "강수량", "평균풍속", "최대풍속", "평균습도"],
    hint: "기상청 ASOS 커넥터 자동 수집 가능. 수동 시 기상청 기후통계 참조",
  },
  noise_vibration: {
    indicators: ["소음_Leq_주간", "소음_Leq_야간", "진동_Lv_주간"],
    hint: "소음진동 현장 측정 결과 또는 환경소음측정망 자료",
  },
  ecology: {
    indicators: ["식물상_종수", "동물상_종수", "법정보호종", "비오톱_유형", "녹지자연도"],
    hint: "현장 생태조사 결과 자료",
  },
};

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

          {/* 권장 지표 안내 */}
          {!isEdit && RECOMMENDED_INDICATORS[form.category] && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm dark:border-blue-800 dark:bg-blue-950">
              <p className="mb-1.5 font-medium text-blue-700 dark:text-blue-300">
                권장 지표
              </p>
              <div className="mb-1 flex flex-wrap gap-1">
                {RECOMMENDED_INDICATORS[form.category]!.indicators.map(
                  (ind) => (
                    <button
                      key={ind}
                      type="button"
                      className="inline-flex items-center rounded border border-blue-300 bg-white px-1.5 py-0.5 text-xs text-blue-800 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800"
                      onClick={() =>
                        setForm((f) => ({ ...f, indicator: ind }))
                      }
                    >
                      {ind}
                    </button>
                  ),
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {RECOMMENDED_INDICATORS[form.category]!.hint}
              </p>
            </div>
          )}

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
