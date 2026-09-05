"use client";

import * as React from "react";
import { AlertTriangle, GitMerge, Newspaper, Radar, RefreshCw, Rocket } from "lucide-react";

import {
  StatusBadge,
  type StoryStatus,
} from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet, apiPost } from "@/lib/api";
import type {
  Story,
  ListResponse,
  IngestionRunResponse,
  IngestionJob,
} from "@/types";

const POLL_INTERVAL = 1200;
const POLL_TIMEOUT = 60000;

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

type StoriesState =
  | { kind: "loading" }
  | { kind: "ok"; data: ListResponse<Story> }
  | { kind: "error"; message: string };

type IngestState =
  | { kind: "idle" }
  | { kind: "polling"; jobId: string; startedAt: number }
  | { kind: "error"; message: string };

type DedupState =
  | { kind: "idle" }
  | { kind: "polling"; jobId: string }
  | { kind: "done"; merged: number }
  | { kind: "error"; message: string };

type ScoutState =
  | { kind: "idle" }
  | { kind: "polling"; jobId: string }
  | { kind: "done"; scored: number }
  | { kind: "error"; message: string };

export default function StoriesPage() {
  const [state, setState] = React.useState<StoriesState>({ kind: "loading" });
  const [ingest, setIngest] = React.useState<IngestState>({ kind: "idle" });
  const [dedup, setDedup] = React.useState<DedupState>({ kind: "idle" });
  const [scout, setScout] = React.useState<ScoutState>({ kind: "idle" });
  const [refreshIndex, setRefreshIndex] = React.useState(0);

  const fetchStories = React.useCallback(() => {
    let cancelled = false;
    apiGet<ListResponse<Story>>("/api/v1/stories?limit=50&offset=0")
      .then((data) => {
        if (!cancelled) setState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Failed to load stories.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    fetchStories();
  }, [fetchStories]);

  React.useEffect(() => {
    return fetchStories();
  }, [fetchStories, refreshIndex]);

  React.useEffect(() => {
    if (ingest.kind !== "polling") return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${ingest.jobId}`)
        .then((job) => {
          if (cancelled) return;
          if (job.status === "COMPLETED" || job.status === "FAILED") {
            setIngest({ kind: "idle" });
            setRefreshIndex((i) => i + 1);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setIngest({ kind: "idle" });
        });
    }, POLL_INTERVAL);

    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setIngest({ kind: "idle" });
        setRefreshIndex((i) => i + 1);
      }
    }, POLL_TIMEOUT);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [ingest]);

  const handleRunIngestion = React.useCallback(() => {
    setIngest({ kind: "error", message: "" });
    apiPost<IngestionRunResponse>("/api/v1/ingestion/run")
      .then((res) => {
        setIngest({
          kind: "polling",
          jobId: res.job_id,
          startedAt: Date.now(),
        });
      })
      .catch((error: unknown) => {
        setIngest({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Failed to start ingestion.",
        });
      });
  }, []);

  const handleRunDedup = React.useCallback(() => {
    setDedup({ kind: "idle" });
    apiPost<IngestionRunResponse>("/api/v1/dedup/run")
      .then((res) => {
        setDedup({ kind: "polling", jobId: res.job_id });
      })
      .catch((error: unknown) => {
        setDedup({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Failed to run deduplication.",
        });
      });
  }, []);

  React.useEffect(() => {
    if (dedup.kind !== "polling") return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${dedup.jobId}`)
        .then((job) => {
          if (cancelled) return;
          if (job.status === "COMPLETED" || job.status === "FAILED") {
            const result = Array.isArray(job.result) ? job.result : [];
            const merged = result.length;
            setDedup(
              job.status === "COMPLETED"
                ? { kind: "done", merged }
                : {
                    kind: "error",
                    message: job.error ?? "Deduplication failed.",
                  }
            );
            setRefreshIndex((i) => i + 1);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setDedup({ kind: "idle" });
        });
    }, POLL_INTERVAL);

    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setDedup({ kind: "idle" });
        setRefreshIndex((i) => i + 1);
      }
    }, POLL_TIMEOUT);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [dedup]);

  const handleRunScout = React.useCallback(() => {
    setScout({ kind: "idle" });
    apiPost<IngestionRunResponse>("/api/v1/scout/run")
      .then((res) => {
        setScout({ kind: "polling", jobId: res.job_id });
      })
      .catch((error: unknown) => {
        setScout({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Failed to run the scout agent.",
        });
      });
  }, []);

  React.useEffect(() => {
    if (scout.kind !== "polling") return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${scout.jobId}`)
        .then((job) => {
          if (cancelled) return;
          if (job.status === "COMPLETED" || job.status === "FAILED") {
            const result = Array.isArray(job.result) ? job.result : [];
            const scored = result.length;
            setScout(
              job.status === "COMPLETED"
                ? { kind: "done", scored }
                : {
                    kind: "error",
                    message: job.error ?? "Scout agent failed.",
                  }
            );
            setRefreshIndex((i) => i + 1);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setScout({ kind: "idle" });
        });
    }, POLL_INTERVAL);

    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setScout({ kind: "idle" });
        setRefreshIndex((i) => i + 1);
      }
    }, POLL_TIMEOUT);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [scout]);

  const isLoading = state.kind === "loading" || ingest.kind === "polling";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">Stories</CardTitle>
              <CardDescription>
                Raw stories ingested from RSS feeds and registered sources,
                awaiting triage before they enter the research and verification
                pipeline.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunScout}
                disabled={scout.kind === "polling"}
              >
                {scout.kind === "polling" ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    Scouting…
                  </>
                ) : (
                  <>
                    <Radar className="size-3.5" />
                    Run scout
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunDedup}
                disabled={dedup.kind === "polling"}
              >
                {dedup.kind === "polling" ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    Deduplicating…
                  </>
                ) : (
                  <>
                    <GitMerge className="size-3.5" />
                    Run dedup
                  </>
                )}
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleRunIngestion}
                disabled={ingest.kind === "polling"}
              >
                {ingest.kind === "polling" ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    Ingesting…
                  </>
                ) : (
                  <>
                    <Rocket className="size-3.5" />
                    Run ingestion
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {scout.kind === "done" && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
              <Radar className="size-3.5 shrink-0" />
              Scout complete — {scout.scored} story/stories scored with a
              category, importance, and research recommendation.
            </div>
          )}
          {scout.kind === "error" && scout.message && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="size-3.5 shrink-0" />
              {scout.message}
            </div>
          )}
          {dedup.kind === "done" && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
              <GitMerge className="size-3.5 shrink-0" />
              Deduplication complete — {dedup.merged} story cluster(s) merged.
            </div>
          )}
          {dedup.kind === "error" && dedup.message && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="size-3.5 shrink-0" />
              {dedup.message}
            </div>
          )}
          {ingest.kind === "error" && ingest.message && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="size-3.5 shrink-0" />
              {ingest.message}
            </div>
          )}

          {state.kind === "loading" && (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          )}

          {state.kind === "error" && ingest.kind !== "error" && (
            <EmptyState
              icon={AlertTriangle}
              title="Failed to load stories"
              description={state.message}
            >
              <Button
                variant="outline"
                size="sm"
                onClick={refresh}
              >
                <RefreshCw className="size-3.5" />
                Retry
              </Button>
            </EmptyState>
          )}

          {state.kind === "ok" && state.data.items.length === 0 && (
            <EmptyState
              icon={Newspaper}
              title="No stories ingested yet"
              description="Stories will appear here after source ingestion begins. Each item starts in the DISCOVERED state and moves through research, verification, drafting, and review."
            >
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunIngestion}
                disabled={ingest.kind === "polling"}
              >
                <Rocket className="size-3.5" />
                Run first ingestion
              </Button>
            </EmptyState>
          )}

          {state.kind === "ok" && state.data.items.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">
                {state.data.total} total stories
                {isLoading && ingest.kind === "polling" && (
                  <span className="ml-2 inline-flex items-center gap-1">
                    <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" />
                    Ingestion running…
                  </span>
                )}
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[30%]">Title</TableHead>
                    <TableHead>Sources</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-center">Importance</TableHead>
                    <TableHead className="text-center">Research</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Discovered</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {state.data.items.map((story) => (
                    <TableRow key={story.id}>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium leading-tight line-clamp-1">
                            {story.title}
                          </span>
                          {story.author && (
                            <span className="text-xs text-muted-foreground">
                              {story.author}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {story.source_names.length > 0
                            ? story.source_names.map((name) => (
                                <span
                                  key={name}
                                  className="inline-flex items-center rounded-md border border-border/60 bg-muted/50 px-1.5 py-0.5 text-xs"
                                >
                                  {name}
                                </span>
                              ))
                            : "—"}
                        </div>
                      </TableCell>
                      <TableCell>
                        {story.category ? (
                          <span className="text-xs">{story.category}</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {story.importance_score == null ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : (
                          <span
                            className={`text-xs font-semibold ${
                              story.importance_score >= 7
                                ? "text-emerald-600"
                                : story.importance_score >= 5
                                  ? "text-amber-600"
                                  : "text-muted-foreground"
                            }`}
                          >
                            {story.importance_score.toFixed(1)}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-center" title={story.scout_reason ?? undefined}>
                        {story.should_research == null ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : story.should_research ? (
                          <span className="inline-flex items-center rounded-md bg-emerald-500/15 px-1.5 py-0.5 text-xs font-medium text-emerald-600">
                            Yes
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                            No
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={story.status as StoryStatus} />
                      </TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground whitespace-nowrap">
                        {formatDateTime(story.discovered_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
