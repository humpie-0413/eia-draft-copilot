"use client";

import type { QaIssue, QaSeverity } from "@/types/qa";
import { SEVERITY_LABELS, SEVERITY_COLORS } from "@/types/qa";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";

const SEVERITY_ICONS: Record<QaSeverity, React.ReactNode> = {
  critical: <AlertCircle className="h-4 w-4 text-red-600" />,
  warning: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
  info: <Info className="h-4 w-4 text-blue-600" />,
};

interface QaIssueListProps {
  issues: QaIssue[];
  filterSeverity?: QaSeverity | null;
}

export function QaIssueList({ issues, filterSeverity }: QaIssueListProps) {
  const filtered = filterSeverity
    ? issues.filter((i) => i.severity === filterSeverity)
    : issues;

  if (filtered.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        {filterSeverity
          ? `${SEVERITY_LABELS[filterSeverity]} 등급의 이슈가 없습니다.`
          : "발견된 이슈가 없습니다."}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {filtered.map((issue, idx) => (
        <Card
          key={`${issue.rule_id}-${issue.section_key}-${idx}`}
          className={`border ${
            issue.severity === "critical"
              ? "border-red-200"
              : issue.severity === "warning"
                ? "border-yellow-200"
                : "border-blue-200"
          }`}
        >
          <CardHeader className="pb-2 pt-3 px-4">
            <div className="flex items-start gap-2">
              {SEVERITY_ICONS[issue.severity]}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <CardTitle className="text-sm font-medium">
                    {issue.title}
                  </CardTitle>
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${SEVERITY_COLORS[issue.severity]}`}
                  >
                    {SEVERITY_LABELS[issue.severity]}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px]">
                    {issue.rule_id}
                  </Badge>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-0">
            <p className="text-sm text-muted-foreground">{issue.message}</p>
            {issue.indicators.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {issue.indicators.map((ind) => (
                  <Badge
                    key={ind}
                    variant="outline"
                    className="text-[10px] font-normal"
                  >
                    {ind}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
