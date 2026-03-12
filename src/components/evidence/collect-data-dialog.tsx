"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { ConnectorInfo, CollectResult } from "@/types/connector";
import { listConnectors, collectData } from "@/lib/connector-api";

/** 커넥터별 입력 파라미터 정의 */
const CONNECTOR_PARAMS: Record<
  string,
  { key: string; label: string; placeholder: string; required?: boolean }[]
> = {
  keco_air: [
    {
      key: "station_name",
      label: "측정소명",
      placeholder: "예: 종로구, 강남구",
      required: true,
    },
    {
      key: "data_term",
      label: "조회 기간",
      placeholder: "DAILY / MONTH / 3MONTH",
    },
  ],
  water_info: [
    {
      key: "year",
      label: "조회 연도",
      placeholder: "예: 2024",
      required: true,
    },
    {
      key: "pt_no",
      label: "측정지점 코드",
      placeholder: "예: 2008A40 (선택)",
    },
  ],
};

interface CollectDataDialogProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

export function CollectDataDialog({
  projectId,
  open,
  onOpenChange,
  onComplete,
}: CollectDataDialogProps) {
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [params, setParams] = useState<Record<string, string>>({});
  const [collecting, setCollecting] = useState(false);
  const [result, setResult] = useState<CollectResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 커넥터 목록 로드
  useEffect(() => {
    if (open) {
      listConnectors()
        .then(setConnectors)
        .catch((err) => console.error("커넥터 목록 조회 실패:", err));
    }
  }, [open]);

  // 다이얼로그 닫힐 때 상태 초기화
  useEffect(() => {
    if (!open) {
      setSelectedKey("");
      setParams({});
      setResult(null);
      setError(null);
      setCollecting(false);
    }
  }, [open]);

  const handleParamChange = useCallback(
    (key: string, value: string) => {
      setParams((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleCollect = async () => {
    if (!selectedKey) return;

    setCollecting(true);
    setResult(null);
    setError(null);

    try {
      const res = await collectData(selectedKey, {
        project_id: projectId,
        params,
      });
      setResult(res);

      if (res.status === "success" && onComplete) {
        onComplete();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "수집 실행 실패";
      setError(message);
    } finally {
      setCollecting(false);
    }
  };

  const currentParams = selectedKey
    ? CONNECTOR_PARAMS[selectedKey] ?? []
    : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>데이터 수집</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 커넥터 선택 */}
          <div className="space-y-2">
            <Label>데이터 소스</Label>
            <Select
              value={selectedKey}
              onValueChange={(v) => {
                setSelectedKey(v);
                setParams({});
                setResult(null);
                setError(null);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="커넥터를 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {connectors.map((c) => (
                  <SelectItem key={c.connector_key} value={c.connector_key}>
                    {c.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 커넥터별 파라미터 입력 */}
          {currentParams.map((p) => (
            <div key={p.key} className="space-y-2">
              <Label>
                {p.label}
                {p.required && <span className="text-destructive"> *</span>}
              </Label>
              <Input
                placeholder={p.placeholder}
                value={params[p.key] ?? ""}
                onChange={(e) => handleParamChange(p.key, e.target.value)}
              />
            </div>
          ))}

          {/* 수집 결과 */}
          {result && (
            <div className="rounded-md border p-3 space-y-1">
              <div className="flex items-center gap-2">
                {result.status === "success" ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
                <span className="text-sm font-medium">
                  {result.status === "success" ? "수집 완료" : "수집 실패"}
                </span>
                <Badge variant={result.status === "success" ? "default" : "destructive"}>
                  {result.evidence_count}건
                </Badge>
              </div>
              {result.error_message && (
                <p className="text-xs text-destructive">
                  {result.error_message}
                </p>
              )}
            </div>
          )}

          {/* 에러 메시지 */}
          {error && (
            <div className="rounded-md border border-destructive p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={collecting}
          >
            닫기
          </Button>
          <Button
            onClick={handleCollect}
            disabled={!selectedKey || collecting}
          >
            {collecting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                수집 중...
              </>
            ) : (
              "수집 실행"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
