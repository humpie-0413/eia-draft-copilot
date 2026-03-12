import { api } from "./api-client";
import type { LLMStatus, EnhanceResponse } from "@/types/llm";

/** LLM adapter 상태 조회 */
export async function getLLMStatus(): Promise<LLMStatus> {
  return api.get("/api/v1/llm/status");
}

/** 섹션 서술문 AI 보강 */
export async function enhanceSectionNarrative(
  projectId: string,
  sectionKey: string,
): Promise<EnhanceResponse> {
  return api.post(`/api/v1/llm/projects/${projectId}/enhance`, {
    section_key: sectionKey,
  });
}
