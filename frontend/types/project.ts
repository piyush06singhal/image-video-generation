import { ImageMetadata } from "./image";

export type ProjectStatus =
  | "created"
  | "uploaded"
  | "validated"
  | "analyzing"
  | "analyzed"
  | "partially_analyzed"
  | "planned"
  | "generating"
  | "assembling"
  | "completed"
  | "failed";

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  images: ImageMetadata[];
  image_count: number;
}

export interface ProjectCreatePayload {
  name: string;
}
