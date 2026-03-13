export type ProjectStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "completed"
  | "archived";

export type ProjectType =
  | "road"
  | "railway"
  | "power_plant"
  | "industrial"
  | "housing"
  | "airport"
  | "port"
  | "dam"
  | "reclamation"
  | "tourism"
  | "military"
  | "other";

/** 사업유형 한글 라벨 */
export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  road: "도로",
  railway: "철도",
  power_plant: "발전소",
  industrial: "산업단지",
  housing: "주거단지",
  airport: "공항",
  port: "항만",
  dam: "댐",
  reclamation: "매립",
  tourism: "관광",
  military: "군사",
  other: "기타",
};

export interface Project {
  id: string;
  name: string;
  description: string | null;
  project_type: ProjectType | null;
  status: ProjectStatus;
  geometry: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}
