/** LLM adapter 상태 */
export interface LLMStatus {
  adapter: "none" | "openai_paid" | "gemini_free";
  available: boolean;
  openai_key_set: boolean;
  google_key_set: boolean;
}

/** 서술문 보강 요청 */
export interface EnhanceRequest {
  section_key: string;
}

/** 서술문 보강 응답 */
export interface EnhanceResponse {
  section_key: string;
  original_narrative: string;
  enhanced_narrative: string;
  adapter_used: string;
  is_fallback: boolean;
}

/** LLM adapter 한글 라벨 */
export const LLM_ADAPTER_LABELS: Record<string, string> = {
  none: "사용 안 함",
  openai_paid: "OpenAI (gpt-4o-mini)",
  gemini_free: "Google Gemini (무료)",
};
