/** 예측 항목 — 지점별 농도 예측 결과 */
export interface PredictionItem {
  label: string;
  distance_m: number;
  pollutant: string;
  predicted_concentration: number;
  background_concentration: number;
  total_concentration: number;
  unit: string;
  standard_value: number | null;
  exceeds_standard: boolean;
}

/** 예측 실행 결과 전체 */
export interface PredictionResult {
  section_key: string;
  model_name: string;
  input_parameters: Record<string, unknown>;
  predictions: PredictionItem[];
  summary: string;
  assumptions: string[];
  limitations: string[];
}

/** 예측 모델 입력 파라미터 정의 */
export interface InputParameter {
  name: string;
  display_name: string;
  unit: string;
  default: number | string | null;
  required: boolean;
  description: string;
}

/** 예측 모델 정보 */
export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  applicable_sections: string[];
  required_inputs: InputParameter[];
}

/** 예측 가능 섹션 키 */
export const PREDICTABLE_SECTIONS: Record<string, string> = {
  air_quality: "대기질",
  noise_vibration: "소음·진동",
  water_quality: "수질",
};
