"use client";

import { useEffect, useState } from "react";
import type { LLMStatus } from "@/types/llm";
import { LLM_ADAPTER_LABELS } from "@/types/llm";
import { getLLMStatus } from "@/lib/llm-api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function LLMStatusCard() {
  const [status, setStatus] = useState<LLMStatus | null>(null);

  useEffect(() => {
    getLLMStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  if (!status) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">LLM 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">현재 모드</span>
          <Badge variant={status.adapter === "none" ? "secondary" : "default"}>
            {LLM_ADAPTER_LABELS[status.adapter] ?? status.adapter}
          </Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">사용 가능</span>
          <Badge variant={status.available ? "default" : "secondary"}>
            {status.available ? "활성" : "비활성"}
          </Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">OpenAI 키</span>
          <span className="text-xs">
            {status.openai_key_set ? "설정됨" : "미설정"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Google 키</span>
          <span className="text-xs">
            {status.google_key_set ? "설정됨" : "미설정"}
          </span>
        </div>
        {status.adapter === "none" && (
          <p className="mt-2 text-xs text-muted-foreground">
            LLM_ADAPTER 환경변수를 설정하면 AI 문체 보강을 사용할 수 있습니다.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
