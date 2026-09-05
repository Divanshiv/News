"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  RefreshCw,
  Rss,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { apiGet, apiPost } from "@/lib/api";
import type {
  Source,
  ListResponse,
  IngestionRunResponse,
  IngestionJob,
  IngestionJobResult,
  SourceIngestResult,
} from "@/types";

const POLL_INTERVAL = 1200;
const POLL_TIMEOUT = 60000;

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function truncateUrl(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname + (parsed.pathname !== "/" ? parsed.pathname : "");
  } catch {
    return url.length > 40 ? url.slice(0, 37) + "…" : url;
  }
}

type SourcesState =
  | { kind: "loading" }
  | { kind: "ok"; data: ListResponse<Source> }
  | { kind: "error"; message: string };

type GlobalIngestState =
  | { kind: "idle" }
  | { kind: "polling"; jobId: string; startedAt: number }
  | { kind: "error"; message: string };

type SourceIngestMap = Record<
  number,
  { kind: "polling"; jobId: string } | { kind: "error"; message: string }
>;

function isSourceIngestResult(
  result: IngestionJobResult,
): result is SourceIngestResult {
  return "fetched" in result;
}

function summarize(results: IngestionJobResult[]): string {
  const ingest = results.filter(isSourceIngestResult);
  const fetched = ingest.reduce((sum, r) => sum + r.fetched, 0);
  const created = ingest.reduce((sum, r) => sum + r.created, 0);
  const skipped = ingest.reduce((sum, r) => sum + r.skipped, 0);
  return `${fetched} fetched \u00b7 ${created} new \u00b7 ${skipped} duplicates`;
}

function reliabilityColor(score: number): string {
  if (score >= 0.8) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 0.5) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export default function SourcesPage() {
  const [state, setState] = React.useState<SourcesState>({ kind: "loading" });
  const [globalIngest, setGlobalIngest] = React.useState<GlobalIngestState>({
    kind: "idle",
  });
  const [sourceIngests, setSourceIngests] = React.useState<SourceIngestMap>({});
  const [lastRunSummary, setLastRunSummary] = React.useState<string | null>(
    null,
  );
  const [refreshIndex, setRefreshIndex] = React.useState(0);

  const fetchSources = React.useCallback(() => {
    let cancelled = false;
    apiGet<ListResponse<Source>>("/api/v1/sources?limit=200")
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
                : "Failed to load sources.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    fetchSources();
  }, [fetchSources]);

  React.useEffect(() => {
    return fetchSources();
  }, [fetchSources, refreshIndex]);

  React.useEffect(() => {
    if (globalIngest.kind !== "polling") return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${globalIngest.jobId}`)
        .then((job) => {
          if (cancelled) return;
          if (job.status === "COMPLETED" || job.status === "FAILED") {
            if (job.status === "COMPLETED" && job.result) {
              setLastRunSummary(summarize(job.result));
            }
            setGlobalIngest({ kind: "idle" });
            setRefreshIndex((i) => i + 1);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setGlobalIngest({ kind: "idle" });
        });
    }, POLL_INTERVAL);
    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setGlobalIngest({ kind: "idle" });
        setRefreshIndex((i) => i + 1);
      }
    }, POLL_TIMEOUT);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [globalIngest]);

  React.useEffect(() => {
    const pollingEntries = Object.entries(sourceIngests).filter(
      (entry): entry is [string, { kind: "polling"; jobId: string }] =>
        entry[1].kind === "polling",
    );
    if (pollingEntries.length === 0) return;
    let cancelled = false;

    const timer = window.setInterval(() => {
      if (cancelled) return;
      for (const [sourceId, info] of pollingEntries) {
        apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${info.jobId}`)
          .then((job) => {
            if (cancelled) return;
            if (job.status === "COMPLETED" || job.status === "FAILED") {
              setSourceIngests((prev) => {
                const next = { ...prev };
                delete next[Number(sourceId)];
                return next;
              });
              setRefreshIndex((i) => i + 1);
            }
          })
          .catch(() => {
            if (cancelled) return;
            setSourceIngests((prev) => {
              const next = { ...prev };
              delete next[Number(sourceId)];
              return next;
            });
          });
      }
    }, POLL_INTERVAL);
    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setSourceIngests({});
        setRefreshIndex((i) => i + 1);
      }
    }, POLL_TIMEOUT);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [sourceIngests]);

  const handleIngestAll = React.useCallback(() => {
    setGlobalIngest({ kind: "error", message: "" });
    apiPost<IngestionRunResponse>("/api/v1/ingestion/run")
      .then((res) => {
        setGlobalIngest({
          kind: "polling",
          jobId: res.job_id,
          startedAt: Date.now(),
        });
      })
      .catch((error: unknown) => {
        setGlobalIngest({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Failed to start ingestion.",
        });
      });
  }, []);

  const handleFetchSource = React.useCallback((sourceId: number) => {
    setSourceIngests((prev) => ({
      ...prev,
      [sourceId]: { kind: "error", message: "" },
    }));
    apiPost<IngestionRunResponse>(
      `/api/v1/ingestion/sources/${sourceId}/fetch`,
    )
      .then((res) => {
        setSourceIngests((prev) => ({
          ...prev,
          [sourceId]: { kind: "polling", jobId: res.job_id },
        }));
      })
      .catch((error: unknown) => {
        setSourceIngests((prev) => ({
          ...prev,
          [sourceId]: {
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Failed to start fetch.",
          },
        }));
      });
  }, []);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">Sources</CardTitle>
              <CardDescription>
                Manage the RSS feeds and registered outlets that feed the
                ingestion stage. Source health and output volume are tracked
                here.
              </CardDescription>
            </div>
            <Button
              variant="default"
              size="sm"
              onClick={handleIngestAll}
              disabled={globalIngest.kind === "polling"}
            >
              {globalIngest.kind === "polling" ? (
                <>
                  <RefreshCw className="size-3.5 animate-spin" />
                  Ingesting…
                </>
              ) : (
                <>
                  <Download className="size-3.5" />
                  Ingest all
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {globalIngest.kind === "error" && globalIngest.message && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="size-3.5 shrink-0" />
              {globalIngest.message}
            </div>
          )}

          {lastRunSummary && globalIngest.kind === "idle" && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">
              <CheckCircle2 className="size-3.5 shrink-0" />
              Last run: {lastRunSummary}
            </div>
          )}

          {state.kind === "loading" && (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          )}

          {state.kind === "error" && (
            <EmptyState
              icon={AlertTriangle}
              title="Failed to load sources"
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
              icon={Rss}
              title="No sources configured"
              description="RSS feeds and sources will be registered here and passed to the ingestion pipeline. Source status and last-fetch times will be shown."
            />
          )}

          {state.kind === "ok" && state.data.items.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">
                {state.data.total} sources
                {state.data.items.filter((s) => s.active).length > 0 && (
                  <span>
                    {" \u00b7 "}
                    {state.data.items.filter((s) => s.active).length} active
                  </span>
                )}
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[22%]">Name</TableHead>
                    <TableHead className="w-[20%]">Feed URL</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Reliability</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Last Fetched</TableHead>
                    <TableHead className="w-20 text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {state.data.items.map((source) => {
                    const ingestState = sourceIngests[source.id];
                    const isFetchingThis = ingestState?.kind === "polling";
                    const hasError = !!source.last_fetch_error;
                    return (
                      <TableRow key={source.id}>
                        <TableCell>
                          <span className="font-medium">{source.name}</span>
                        </TableCell>
                        <TableCell>
                          {source.rss_url ? (
                            <span
                              className="text-xs text-muted-foreground"
                              title={source.rss_url}
                            >
                              {truncateUrl(source.rss_url)}
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              —
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {source.category ? (
                            <span className="text-xs">{source.category}</span>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              —
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-xs">{source.source_type}</span>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`text-xs font-medium tabular-nums ${reliabilityColor(source.reliability_score)}`}
                          >
                            {source.reliability_score.toFixed(2)}
                          </span>
                        </TableCell>
                        <TableCell>
                          {source.active ? (
                            <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                              active
                            </Badge>
                          ) : (
                            <Badge className="border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400">
                              inactive
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {hasError ? (
                            <Badge
                              className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                              title={source.last_fetch_error!}
                            >
                              <XCircle className="size-3" />
                              error
                            </Badge>
                          ) : source.last_fetched_at ? (
                            <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                              ok
                            </Badge>
                          ) : (
                            <Badge className="border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400">
                              pending
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground whitespace-nowrap">
                          {formatDateTime(source.last_fetched_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="outline"
                            size="xs"
                            onClick={() => handleFetchSource(source.id)}
                            disabled={isFetchingThis || !source.rss_url}
                            title={source.rss_url ? "Fetch feed" : "No RSS feed — reference source"}
                          >
                            {isFetchingThis ? (
                              <RefreshCw className="size-3 animate-spin" />
                            ) : (
                              <Download className="size-3" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
