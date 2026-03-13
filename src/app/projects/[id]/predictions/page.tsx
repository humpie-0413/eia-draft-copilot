"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPredictionModels, runPrediction } from "@/lib/prediction-api";
import type { ModelInfo, PredictionResult, InputParameter } from "@/types/prediction";
import { PREDICTABLE_SECTIONS } from "@/types/prediction";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowLeft,
  Activity,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from "lucide-react";

// ─── 섹션별 모델/결과 상태 ───
interface SectionPredictionState {
  sectionKey: string;
  model: ModelInfo | null;
  // 파라미터 입력값 (string → 전송 전 파싱)
  paramValues: Record<string, string>;
  useBackgroundData: boolean;
  loading: boolean;
  result: PredictionResult | null;
  error: string | null;
  // 전제/한계 영역 펼침 여부
  metaExpanded: boolean;
}

// ─── 파라미터 입력 폼 컴포넌트 ───
function ParameterForm({
  parameters,
  values,
  onChange,
}: {
  parameters: InputParameter[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}) {
  if (parameters.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        이 모델은 별도 파라미터 없이 실행됩니다.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {parameters.map((param) => (
        <div key={param.name} className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Label htmlFor={`param-${param.name}`} className="text-xs font-medium">
              {param.display_name}
              {param.required && (
                <span className="ml-0.5 text-destructive">*</span>
              )}
            </Label>
            {param.unit && (
              <span className="text-xs text-muted-foreground">({param.unit})</span>
            )}
          </div>
          <Input
            id={`param-${param.name}`}
            type="number"
            value={values[param.name] ?? ""}
            onChange={(e) => onChange(param.name, e.target.value)}
            placeholder={
              param.default !== null ? String(param.default) : "값 입력"
            }
            className="h-8 text-sm"
          />
          {param.description && (
            <p className="text-[11px] text-muted-foreground leading-tight">
              {param.description}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── 예측 결과 테이블 컴포넌트 ───
function PredictionResultTable({
  result,
}: {
  result: PredictionResult;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-28">지점/거리</TableHead>
          <TableHead>오염물질</TableHead>
          <TableHead className="text-right">기여농도</TableHead>
          <TableHead className="text-right">현황(배경)</TableHead>
          <TableHead className="text-right">합산</TableHead>
          <TableHead className="text-right">기준</TableHead>
          <TableHead className="w-20 text-center">판정</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {result.predictions.map((item, idx) => (
          <TableRow
            key={idx}
            className={item.exceeds_standard ? "bg-red-50 hover:bg-red-100" : ""}
          >
            <TableCell className="font-medium text-xs">
              <div>{item.label}</div>
              {item.distance_m > 0 && (
                <div className="text-muted-foreground">{item.distance_m}m</div>
              )}
            </TableCell>
            <TableCell className="text-xs">{item.pollutant}</TableCell>
            <TableCell className="text-right text-xs tabular-nums">
              {item.predicted_concentration.toFixed(4)}
            </TableCell>
            <TableCell className="text-right text-xs tabular-nums">
              {item.background_concentration.toFixed(4)}
            </TableCell>
            <TableCell className="text-right text-xs tabular-nums font-medium">
              {item.total_concentration.toFixed(4)}{" "}
              <span className="text-muted-foreground font-normal">{item.unit}</span>
            </TableCell>
            <TableCell className="text-right text-xs tabular-nums">
              {item.standard_value !== null ? (
                <>
                  {item.standard_value}{" "}
                  <span className="text-muted-foreground">{item.unit}</span>
                </>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell className="text-center">
              {item.standard_value !== null ? (
                item.exceeds_standard ? (
                  <Badge
                    variant="destructive"
                    className="text-[10px] px-1.5 gap-0.5"
                  >
                    <XCircle className="h-3 w-3" />
                    초과
                  </Badge>
                ) : (
                  <Badge
                    variant="secondary"
                    className="text-[10px] px-1.5 gap-0.5 bg-green-100 text-green-800 border-green-200"
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    적합
                  </Badge>
                )
              ) : (
                <span className="text-xs text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ─── 메인 페이지 ───
export default function PredictionsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // 섹션별 예측 상태 초기화
  const [sectionStates, setSectionStates] = useState<
    Record<string, SectionPredictionState>
  >({});

  // ─── 모델 목록 로딩 ───
  const fetchModels = useCallback(async () => {
    setModelsLoading(true);
    setModelsError(null);
    try {
      const data = await getPredictionModels();
      setModels(data);

      // 각 예측 가능 섹션에 해당 모델 매핑, 상태 초기화
      const initialStates: Record<string, SectionPredictionState> = {};
      for (const sectionKey of Object.keys(PREDICTABLE_SECTIONS)) {
        const matched = data.find((m) =>
          m.applicable_sections.includes(sectionKey),
        );
        const defaultParamValues: Record<string, string> = {};
        if (matched) {
          for (const p of matched.required_inputs) {
            defaultParamValues[p.name] =
              p.default !== null ? String(p.default) : "";
          }
        }
        initialStates[sectionKey] = {
          sectionKey,
          model: matched ?? null,
          paramValues: defaultParamValues,
          useBackgroundData: true,
          loading: false,
          result: null,
          error: null,
          metaExpanded: false,
        };
      }
      setSectionStates(initialStates);
    } catch (err) {
      console.error("예측 모델 목록 조회 실패:", err);
      setModelsError("예측 모델 목록을 불러오지 못했습니다.");
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // ─── 파라미터 변경 ───
  const handleParamChange = (
    sectionKey: string,
    paramName: string,
    value: string,
  ) => {
    setSectionStates((prev) => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        paramValues: {
          ...prev[sectionKey].paramValues,
          [paramName]: value,
        },
      },
    }));
  };

  // ─── 배경 데이터 토글 ───
  const handleBackgroundToggle = (sectionKey: string, checked: boolean) => {
    setSectionStates((prev) => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        useBackgroundData: checked,
      },
    }));
  };

  // ─── 메타 영역 토글 ───
  const handleMetaToggle = (sectionKey: string) => {
    setSectionStates((prev) => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        metaExpanded: !prev[sectionKey].metaExpanded,
      },
    }));
  };

  // ─── 예측 실행 ───
  const handleRunPrediction = async (sectionKey: string) => {
    const state = sectionStates[sectionKey];
    if (!state) return;

    // 파라미터를 숫자로 변환 (가능한 경우)
    const parsedParameters: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(state.paramValues)) {
      const num = Number(val);
      parsedParameters[key] = isNaN(num) || val === "" ? val : num;
    }

    setSectionStates((prev) => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        loading: true,
        error: null,
        result: null,
      },
    }));

    try {
      const result = await runPrediction(projectId, sectionKey, {
        model_name: state.model?.name,
        parameters: parsedParameters,
        use_background_data: state.useBackgroundData,
      });
      setSectionStates((prev) => ({
        ...prev,
        [sectionKey]: {
          ...prev[sectionKey],
          loading: false,
          result,
        },
      }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "예측 실행 중 오류가 발생했습니다.";
      console.error(`${sectionKey} 예측 실패:`, err);
      setSectionStates((prev) => ({
        ...prev,
        [sectionKey]: {
          ...prev[sectionKey],
          loading: false,
          error: message,
        },
      }));
    }
  };

  // ─── 렌더링 ───
  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}/draft`}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">영향 예측</h2>
            <p className="text-sm text-muted-foreground">
              대기질·소음·수질 수치 모델 기반 환경 영향 예측
            </p>
          </div>
        </div>
      </div>

      {/* 모델 목록 로딩 중 */}
      {modelsLoading && (
        <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">예측 모델 목록 로딩 중…</span>
        </div>
      )}

      {/* 모델 목록 로딩 오류 */}
      {modelsError && (
        <div className="flex items-center gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-medium">모델 로딩 실패</p>
            <p className="mt-0.5 text-xs opacity-80">{modelsError}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchModels}
            className="ml-auto shrink-0"
          >
            다시 시도
          </Button>
        </div>
      )}

      {/* 섹션별 예측 카드 */}
      {!modelsLoading &&
        !modelsError &&
        Object.entries(PREDICTABLE_SECTIONS).map(([sectionKey, sectionLabel]) => {
          const state = sectionStates[sectionKey];
          if (!state) return null;

          return (
            <Card key={sectionKey}>
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{sectionLabel}</CardTitle>
                    {state.model ? (
                      <CardDescription className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-[11px]">
                          {state.model.display_name}
                        </Badge>
                        <span>{state.model.description}</span>
                      </CardDescription>
                    ) : (
                      <CardDescription>
                        <Badge
                          variant="outline"
                          className="text-[11px] text-muted-foreground"
                        >
                          모델 없음
                        </Badge>
                        <span className="ml-2">
                          이 섹션에 대한 예측 모델이 등록되지 않았습니다.
                        </span>
                      </CardDescription>
                    )}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-5">
                {state.model ? (
                  <>
                    {/* 파라미터 입력 폼 */}
                    <ParameterForm
                      parameters={state.model.required_inputs}
                      values={state.paramValues}
                      onChange={(name, value) =>
                        handleParamChange(sectionKey, name, value)
                      }
                    />

                    {/* 배경 데이터 옵션 + 실행 버튼 */}
                    <div className="flex items-center justify-between border-t pt-4">
                      <div className="flex items-center gap-3">
                        <Switch
                          id={`bg-${sectionKey}`}
                          checked={state.useBackgroundData}
                          onCheckedChange={(checked) =>
                            handleBackgroundToggle(sectionKey, checked)
                          }
                        />
                        <Label
                          htmlFor={`bg-${sectionKey}`}
                          className="cursor-pointer text-sm"
                        >
                          배경 데이터 사용
                        </Label>
                        <span className="text-xs text-muted-foreground">
                          (현황 측정값을 합산에 포함)
                        </span>
                      </div>
                      <Button
                        onClick={() => handleRunPrediction(sectionKey)}
                        disabled={state.loading}
                        size="sm"
                      >
                        {state.loading ? (
                          <>
                            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                            예측 중…
                          </>
                        ) : (
                          <>
                            <Activity className="mr-1.5 h-4 w-4" />
                            예측 실행
                          </>
                        )}
                      </Button>
                    </div>

                    {/* 에러 알림 */}
                    {state.error && (
                      <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>{state.error}</span>
                      </div>
                    )}

                    {/* 예측 결과 */}
                    {state.result && (
                      <div className="space-y-4 border-t pt-4">
                        {/* 예측 서술문 */}
                        <div className="rounded-md bg-muted/50 p-3">
                          <p className="text-sm leading-relaxed">
                            {state.result.summary}
                          </p>
                        </div>

                        {/* 결과 테이블 */}
                        {state.result.predictions.length > 0 ? (
                          <PredictionResultTable result={state.result} />
                        ) : (
                          <p className="py-4 text-center text-sm text-muted-foreground">
                            예측 결과 데이터가 없습니다.
                          </p>
                        )}

                        {/* 전제 조건 + 한계 (접히는 영역) */}
                        {(state.result.assumptions.length > 0 ||
                          state.result.limitations.length > 0) && (
                          <div className="border rounded-md">
                            <button
                              type="button"
                              onClick={() => handleMetaToggle(sectionKey)}
                              className="flex w-full items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-muted/40 transition-colors"
                            >
                              <span>전제 조건 및 모델 한계</span>
                              {state.metaExpanded ? (
                                <ChevronUp className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              )}
                            </button>
                            {state.metaExpanded && (
                              <div className="border-t px-4 py-3 space-y-3">
                                {state.result.assumptions.length > 0 && (
                                  <div>
                                    <p className="mb-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                      전제 조건
                                    </p>
                                    <ul className="space-y-1">
                                      {state.result.assumptions.map(
                                        (item, i) => (
                                          <li
                                            key={i}
                                            className="flex items-start gap-2 text-sm"
                                          >
                                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />
                                            {item}
                                          </li>
                                        ),
                                      )}
                                    </ul>
                                  </div>
                                )}
                                {state.result.limitations.length > 0 && (
                                  <div>
                                    <p className="mb-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                      모델 한계
                                    </p>
                                    <ul className="space-y-1">
                                      {state.result.limitations.map(
                                        (item, i) => (
                                          <li
                                            key={i}
                                            className="flex items-start gap-2 text-sm"
                                          >
                                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-400" />
                                            {item}
                                          </li>
                                        ),
                                      )}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground py-2">
                    현재 이 섹션에 대한 예측 모델이 없습니다. 모델이 등록되면
                    자동으로 표시됩니다.
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
    </div>
  );
}
