/**
 * Shared types matching the backend API contracts (app/api + app/schemas).
 * Keep these in sync with the FastAPI response models when the backend changes.
 */

export type StoryStatus =
  | "DISCOVERED"
  | "RESEARCHING"
  | "VERIFICATION"
  | "DRAFT"
  | "REVIEW"
  | "APPROVED"
  | "PUBLISHED"
  | "REJECTED"
  | "MERGED";

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type Story = {
  id: number;
  title: string;
  slug: string;
  summary: string | null;
  category: string | null;
  status: StoryStatus;
  importance_score: number | null;
  confidence_score: number | null;
  discovered_at: string;
  updated_at: string;
  url: string | null;
  author: string | null;
  image_url: string | null;
  source_published_at: string | null;
  source_names: string[];
};

export type Source = {
  id: number;
  name: string;
  url: string;
  rss_url: string | null;
  source_type: string;
  category: string | null;
  reliability_score: number;
  active: boolean;
  license_notes: string | null;
  created_at: string;
  updated_at: string;
  last_fetched_at: string | null;
  last_fetch_error: string | null;
};

export type IngestionJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED";

export type IngestionRunResponse = {
  job_id: string;
  job_name: string;
  status: IngestionJobStatus;
};

export type SourceIngestResult = {
  source_id: number;
  source_name: string;
  status: "ok" | "error";
  fetched: number;
  created: number;
  skipped: number;
  error: string | null;
};

export type IngestionJob = {
  job_id: string;
  job_name: string;
  status: IngestionJobStatus;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: SourceIngestResult[] | null;
};