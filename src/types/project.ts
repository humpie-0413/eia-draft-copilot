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
  | "other";

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
