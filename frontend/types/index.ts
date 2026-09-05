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
  should_research: boolean | null;
  scout_reason: string | null;
  scouted_at: string | null;
  researched_at: string | null;
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

export type DedupRunResult = {
  keep_id: number;
  absorbed_ids: number[];
  moved_links: number;
};

export type ScoutRunResult =
  | {
      story_id: number;
      title: string;
      error: string;
    }
  | {
      story_id: number;
      title: string;
      should_research: boolean;
      importance: number;
      category: string | null;
      reason: string;
    };

export type ResearchRunResult =
  | {
      story_id: number;
      title: string;
      error: string;
    }
  | {
      story_id: number;
      title: string;
      sources: number;
      claims: number;
      run_id: number;
    };

export type IngestionJobResult =
  | SourceIngestResult
  | DedupRunResult
  | ScoutRunResult
  | ResearchRunResult;

export type IngestionJob = {
  job_id: string;
  job_name: string;
  status: IngestionJobStatus;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: IngestionJobResult[] | null;
};

export type JobSummary = {
  job_id: string;
  job_name: string;
  status: IngestionJobStatus;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
};

export type ServiceConfig = {
  app_name: string;
  app_version: string;
  environment: string;
  llm_provider: string;
  ollama_url: string;
  ollama_model: string;
  openai_model?: string | null;
  anthropic_model?: string | null;
};

export type Article = {
  id: number;
  story_id: number;
  headline: string;
  subheadline: string | null;
  summary: string | null;
  body: string | null;
  seo_title: string | null;
  seo_description: string | null;
  status: string;
  published_at: string | null;
  updated_at: string;
};

export type ArticleWithStory = Article & {
  story_title: string | null;
  story_category: string | null;
  story_slug: string | null;
  story_confidence: number | null;
  story_url: string | null;
};

export type DedupCandidate = {
  story_id_a: number;
  title_a: string;
  story_id_b: number;
  title_b: string;
  score: number;
};

export type ResearchRunRecord = {
  id: number;
  story_id: number;
  agent_name: string;
  status: string;
  output: {
    sources: {
      url: string;
      title: string;
      snippet: string;
      tier: string;
      relevance: number;
      fetched: boolean;
    }[];
  } | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type StoryResearchSource = {
  source_id: number;
  name: string | null;
  url: string | null;
  relationship: string;
  relevance_score: number | null;
};

export type ResearchEvidence = {
  id: number;
  evidence_text: string;
  url: string | null;
  source_id: number | null;
};

export type ResearchClaim = {
  id: number;
  claim_text: string;
  status: string;
  confidence_score: number | null;
  evidences: ResearchEvidence[];
};

export type StoryResearch = {
  story_id: number;
  title: string;
  runs: ResearchRunRecord[];
  sources: StoryResearchSource[];
  claims: ResearchClaim[];
};