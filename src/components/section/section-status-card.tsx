"use client";

import type { SectionStatus, SectionStatusValue } from "@/types/section";
import { SECTION_STATUS_LABELS } from "@/types/section";
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
};

interface SectionStatusCardProps {
  section: SectionStatus;
  onClick?: () => void;
}

export function SectionStatusCard({ section, onClick }: SectionStatusCardProps) {
  const pct = Math.round(section.coverage_ratio * 100);

  return (
    <Card
      className={`cursor-pointer transition-shadow hover:shadow-md ${
        onClick ? "hover:ring-2 hover:ring-primary/20" : ""
      }`}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-sm font-medium">
            {section.title}
          </CardTitle>
          <Badge
            variant="secondary"
            className={`text-xs ${STATUS_COLORS[section.status]}`}
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
