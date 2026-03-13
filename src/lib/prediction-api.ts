import { api } from "./api-client";
import type { ModelInfo, PredictionResult } from "@/types/prediction";

/** 사용 가능한 예측 모델 목록 조회 */
export async function getPredictionModels(): Promise<ModelInfo[]> {
  return api.get("/api/v1/prediction-models");
}

/** 섹션별 영향 예측 실행 */
export async function runPrediction(
  projectId: string,
  sectionKey: string,
  params?: {
    model_name?: string;
    parameters?: Record<string, unknown>;
    use_background_data?: boolean;
  },
): Promise<PredictionResult> {
  return api.post(
    `/api/v1/projects/${projectId}/predict/${sectionKey}`,
    params ?? { use_background_data: true },
  );
}
