"use client";

import type { SectionStatus, SectionStatusValue } from "@/types/section";
import { SECTION_STATUS_LABELS, SECTION_SCOPE_LABELS } from "@/types/section";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const STATUS_COLORS: Record<SectionStatusValue, string> = {
  empty: "bg-gray-100 text-gray-600",
  partial: "bg-yellow-100 text-yellow-700",
  complete: "bg-green-100 text-green-700",
  auto_filled: "bg-blue-100 text-blue-700",
  evidence_draft: "bg-orange-100 text-orange-700",
  expert_required: "bg-red-100 text-red-700",
  not_applicable: "bg-gray-100 text-gray-500",
};

const SCOPE_COLORS: Record<string, string> = {
  required: "bg-red-50 text-red-700 border-red-200",
  recommended: "bg-amber-50 text-amber-700 border-amber-200",
  optional: "bg-gray-50 text-gray-500 border-gray-200",
};

interface SectionStatusCardProps {
  section: SectionStatus;
  onClick?: () => void;
}

export function SectionStatusCard({ section, onClick }: SectionStatusCardProps) {
  const pct = Math.round(section.coverage_ratio * 100);
  const scopeLabel = SECTION_SCOPE_LABELS[section.scope];

  return (
    <Card
      className={`cursor-pointer transition-shadow hover:shadow-md ${
        onClick ? "hover:ring-2 hover:ring-primary/20" : ""
      }${section.scope === "required" && section.status === "expert_required" ? " ring-1 ring-red-300" : ""}`}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-1">
          <div className="flex items-center gap-1.5">
            <CardTitle className="text-sm font-medium">
              {section.title}
            </CardTitle>
            {scopeLabel && (
              <Badge
                variant="outline"
                className={`text-[10px] px-1.5 py-0 leading-4 ${SCOPE_COLORS[section.scope] ?? ""}`}
              >
                {scopeLabel}
              </Badge>
            )}
          </div>
          <Badge
            variant="secondary"
            className={`text-xs shrink-0 ${STATUS_COLORS[section.status]}`}
          >
            {SECTION_STATUS_LABELS[section.status]}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{section.description}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 충족도 바 */}
        <div>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              필수 지표 {section.fulfilled_count}/{section.required_count}
            </span>
            <span className="font-medium">{pct}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full rounded-full transition-all ${
                pct === 100
                  ? "bg-green-500"
                  : pct > 0
                    ? "bg-yellow-500"
                    : "bg-gray-300"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* 지표 목록 */}
        <div className="space-y-1">
          {section.required_indicators.map((ind) => (
            <div
              key={ind.name}
              className="flex items-center justify-between text-xs"
            >
              <span
                className={
                  ind.fulfilled ? "text-foreground" : "text-muted-foreground"
                }
              >
                {ind.fulfilled ? "✓" : "○"} {ind.name}
              </span>
              {ind.evidence_count > 0 && (
                <span className="text-muted-foreground">
                  {ind.evidence_count}건
                </span>
              )}
            </div>
          ))}
        </div>

        {/* 전체 증거 수 */}
        <div className="border-t pt-2 text-xs text-muted-foreground">
          전체 증거 {section.total_evidence_count}건
        </div>
      </CardContent>
    </Card>
  );
}
