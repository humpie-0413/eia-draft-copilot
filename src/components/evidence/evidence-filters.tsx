"use client";

import { EVIDENCE_CATEGORIES, type EvidenceCategory } from "@/types/evidence";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

interface EvidenceFiltersProps {
  category: EvidenceCategory | undefined;
  screeningOnly: boolean | undefined;
  onCategoryChange: (category: EvidenceCategory | undefined) => void;
  onScreeningOnlyChange: (value: boolean | undefined) => void;
}

export function EvidenceFilters({
  category,
  screeningOnly,
  onCategoryChange,
  onScreeningOnlyChange,
}: EvidenceFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* 분야 필터 */}
      <div className="flex items-center gap-2">
        <Label className="text-sm font-medium whitespace-nowrap">분야</Label>
        <Select
          value={category ?? "__all__"}
          onValueChange={(v) =>
            onCategoryChange(v === "__all__" ? undefined : (v as EvidenceCategory))
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="전체 분야" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">전체 분야</SelectItem>
            {Object.entries(EVIDENCE_CATEGORIES).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 스크리닝 전용 토글 */}
      <div className="flex items-center gap-2">
        <Switch
          id="screening-toggle"
          checked={screeningOnly ?? false}
          onCheckedChange={(checked) =>
            onScreeningOnlyChange(checked ? true : undefined)
          }
        />
        <Label htmlFor="screening-toggle" className="text-sm cursor-pointer">
          스크리닝 전용만 보기
        </Label>
      </div>

      {/* 필터 초기화 */}
      {(category || screeningOnly) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            onCategoryChange(undefined);
            onScreeningOnlyChange(undefined);
          }}
        >
          <X className="mr-1 h-3 w-3" />
          필터 초기화
        </Button>
      )}
    </div>
  );
}
