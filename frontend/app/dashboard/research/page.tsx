"use client";

import * as React from "react";
import { AlertTriangle, ExternalLink, RefreshCw, Telescope } from "lucide-react";

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
import { StatusBadge } from "@/components/status-badge";
import { apiGet, apiPost } from "@/lib/api";
import type {
  Story,
  ListResponse,
  IngestionJob,
  IngestionRunResponse,
  StoryResearch,
} from "@/types";

const POLL_INTERVAL = 30000;
const JOB_POLL_INTERVAL = 1500;
const JOB_POLL_TIMEOUT = 180000;

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function importanceTone(score: number | null): string {
  if (score === null) return "text-muted-foreground";
  if (score >= 7) return "text-emerald-600 dark:text-emerald-400 font-medium";
  if (score >= 5) return "text-amber-600 dark:text-amber-400 font-medium";
  return "text-muted-foreground";
}

type ResearchRunState =
  | { kind: "idle" }
  | { kind: "polling"; jobId: string }
  | { kind: "done"; researched: number }
  | { kind: "error"; message: string };

type PackageState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; data: StoryResearch }
  | { kind: "error"; message: string };

export default function ResearchPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ListResponse<Story> }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [tick, setTick] = React.useState(0);
  const [selectedStoryId, setSelectedStoryId] = React.useState<number | null>(null);
  const [research, setResearch] = React.useState<ResearchRunState>({ kind: "idle" });
  const [packageState, setPackageState] = React.useState<PackageState>({ kind: "idle" });

  const load = React.useCallback(() => {
    let cancelled = false;
    apiGet<ListResponse<Story>>("/api/v1/stories?limit=100&status=RESEARCHING")
      .then((data) => {
        if (!cancelled) setState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Failed to load research queue.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => load(), [load, tick]);

  React.useEffect(() => {
    const timer = window.setInterval(() => setTick((t) => t + 1), POLL_INTERVAL);
    return () => window.clearInterval(timer);
  }, []);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  }, []);

  const handleRunResearch = React.useCallback(() => {
    setResearch({ kind: "idle" });
    apiPost<IngestionRunResponse>("/api/v1/research/run")
      .then((res) => {
        setResearch({ kind: "polling", jobId: res.job_id });
      })
      .catch((error: unknown) => {
        setResearch({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Failed to run research.",
        });
      });
  }, []);

  React.useEffect(() => {
    if (research.kind !== "polling") return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      apiGet<IngestionJob>(`/api/v1/ingestion/jobs/${research.jobId}`)
        .then((job) => {
          if (cancelled) return;
          if (job.status === "COMPLETED" || job.status === "FAILED") {
            const result = Array.isArray(job.result) ? job.result : [];
            const researched = result.length;
            setResearch(
              job.status === "COMPLETED"
                ? { kind: "done", researched }
                : {
                    kind: "error",
                    message: job.error ?? "Research agent failed.",
                  }
            );
            setTick((t) => t + 1);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setResearch({ kind: "idle" });
        });
    }, JOB_POLL_INTERVAL);

    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        window.clearInterval(timer);
        setResearch({ kind: "idle" });
        setTick((t) => t + 1);
      }
    }, JOB_POLL_TIMEOUT);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.clearTimeout(timeout);
    };
  }, [research]);

  React.useEffect(() => {
    if (selectedStoryId === null) {
      setPackageState({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setPackageState({ kind: "loading" });
    apiGet<StoryResearch>(`/api/v1/research/runs/${selectedStoryId}`)
      .then((data) => {
        if (!cancelled) setPackageState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setPackageState({
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Failed to load the research package.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [selectedStoryId, tick]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Research queue</CardTitle>
            <CardDescription>
              Stories actively being researched by agents (status RESEARCHING). Research
              runs assemble background, context, and corroborating references before any
              claim is written. Select a row to inspect its research package.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRunResearch}
              disabled={research.kind === "polling"}
            >
              {research.kind === "polling" ? (
                <>
                  <RefreshCw className="size-3.5 animate-spin" />
                  Researching…
                </>
              ) : (
                <>
                  <Telescope className="size-3.5" />
                  Run research
                </>
              )}
            </Button>
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="size-3.5" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {research.kind === "done" && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
            <Telescope className="size-3.5 shrink-0" />
            Research complete — {research.researched} story/stories researched
            with a package of gathered sources.
          </div>
        )}
        {research.kind === "error" && research.message && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            <AlertTriangle className="size-3.5 shrink-0" />
            {research.message}
          </div>
        )}

        {state.kind === "loading" && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )}

        {state.kind === "error" && (
          <EmptyState
            icon={AlertTriangle}
            title="Failed to load research queue"
            description={state.message}
          >
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="size-3.5" />
              Retry
            </Button>
          </EmptyState>
        )}

        {state.kind === "ok" && state.data.items.length === 0 && (
          <EmptyState
            icon={Telescope}
            title="No stories being researched right now"
            description="Stories move into RESEARCHING from the Story pipeline once you promote them or an agent starts a research run. Choose 'should research' stories in the Stories scout view to queue them here."
          />
        )}

        {state.kind === "ok" && state.data.items.length > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-muted-foreground">{state.data.total} in research</p>
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50%]">Story</TableHead>
                  <TableHead className="w-[15%]">Category</TableHead>
                  <TableHead className="w-[12%]">Importance</TableHead>
                  <TableHead className="w-[12%]">Status</TableHead>
                  <TableHead className="w-[11%] text-right">Discovered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.data.items.map((story) => (
                  <TableRow
                    key={story.id}
                    className={
                      selectedStoryId === story.id
                        ? "cursor-pointer bg-muted/50"
                        : "cursor-pointer"
                    }
                    onClick={() =>
                      setSelectedStoryId((current) =>
                        current === story.id ? null : story.id
                      )
                    }
                  >
                    <TableCell>
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <span className="font-medium truncate">{story.title}</span>
                        {story.scout_reason && (
                          <span className="text-xs text-muted-foreground truncate">
                            {story.scout_reason}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {story.category ? (
                        <Badge variant="outline">{story.category}</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={importanceTone(story.importance_score)}>
                        {story.importance_score !== null
                          ? story.importance_score.toFixed(1)
                          : "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={story.status} />
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(story.discovered_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {selectedStoryId !== null && (
              <PackageViewer
                packageState={packageState}
                onClose={() => setSelectedStoryId(null)}
              />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PackageViewer({
  packageState,
  onClose,
}: {
  packageState: PackageState;
  onClose: () => void;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Research package</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      {packageState.kind === "loading" && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {packageState.kind === "error" && (
        <p className="text-sm text-destructive">{packageState.message}</p>
      )}

      {packageState.kind === "ok" && (
        <div className="flex flex-col gap-4">
          <p className="text-xs text-muted-foreground">{packageState.data.title}</p>

          {packageState.data.runs.length === 0 &&
            packageState.data.sources.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No research package yet for this story.
              </p>
            )}

          {packageState.data.runs.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Runs
              </h4>
              {packageState.data.runs.map((run) => (
                <div
                  key={run.id}
                  className="rounded-md border border-border/60 bg-background/60 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{run.agent_name}</span>
                    <Badge variant="outline">{run.status}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatDate(run.started_at)} → {formatDate(run.completed_at)}
                    {run.output?.sources
                      ? ` · ${run.output.sources.length} source(s) gathered`
                      : ""}
                  </div>
                  {run.error && (
                    <p className="mt-1 text-xs text-destructive">{run.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {packageState.data.sources.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Sources ({packageState.data.sources.length})
              </h4>
              <ul className="flex flex-col gap-1.5">
                {packageState.data.sources.map((source) => (
                  <li
                    key={source.source_id}
                    className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-background/60 px-3 py-2 text-sm"
                  >
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="truncate font-medium">
                        {source.name ?? source.url ?? "Untitled"}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {source.relationship}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {source.relevance_score !== null && (
                        <Badge variant="outline">
                          {source.relevance_score.toFixed(2)}
                        </Badge>
                      )}
                      {source.url && (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground transition-colors hover:text-foreground"
                          title={source.url}
                        >
                          <ExternalLink className="size-3.5" />
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {packageState.data.claims.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Initial claims ({packageState.data.claims.length})
              </h4>
              <ul className="flex flex-col gap-1.5">
                {packageState.data.claims.map((claim) => (
                  <li
                    key={claim.id}
                    className="rounded-md border border-border/60 bg-background/60 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span>{claim.claim_text}</span>
                      <Badge variant="outline">{claim.status}</Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      {claim.confidence_score !== null && (
                        <span>confidence {claim.confidence_score.toFixed(2)}</span>
                      )}
                      {claim.evidences.length > 0 && (
                        <span>· {claim.evidences.length} evidence item(s)</span>
                      )}
                    </div>
                    {claim.evidences.length > 0 && (
                      <ul className="mt-1.5 flex flex-col gap-1">
                        {claim.evidences.map((evidence) => (
                          <li
                            key={evidence.id}
                            className="flex items-center gap-2 text-xs text-muted-foreground"
                          >
                            <span className="min-w-0 flex-1 truncate">
                              {evidence.evidence_text}
                            </span>
                            {evidence.url && (
                              <a
                                href={evidence.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="shrink-0 transition-colors hover:text-foreground"
                                title={evidence.url}
                              >
                                <ExternalLink className="size-3" />
                              </a>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}