"use client";

import * as React from "react";
import { AlertTriangle, Bot, RefreshCw } from "lucide-react";

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
import { apiGet } from "@/lib/api";
import type { JobSummary, IngestionJobStatus } from "@/types";

const JOB_STATUS_TONE: Record<IngestionJobStatus, string> = {
  QUEUED: "border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400",
  RUNNING: "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
  COMPLETED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  FAILED: "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
};

const JOB_LABELS: Record<string, string> = {
  ingest_all: "Ingest all sources",
  ingest_source: "Ingest source",
  dedupe_all: "Deduplicate stories",
  run_scout: "Scout stories",
  research_story: "Research story",
  verify_story: "Verify story",
  generate_article: "Generate article",
  backfill_summaries: "Backfill story summaries",
};

function jobLabel(name: string): string {
  return JOB_LABELS[name] ?? name;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function AgentsPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: JobSummary[] }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [tick, setTick] = React.useState(0);

  const load = React.useCallback(() => {
    let cancelled = false;
    apiGet<JobSummary[]>("/api/v1/jobs?limit=50")
      .then((data) => {
        if (!cancelled) setState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message:
              error instanceof Error ? error.message : "Failed to load agent runs.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => load(), [load, tick]);

  React.useEffect(() => {
    const timer = window.setInterval(() => setTick((t) => t + 1), 15000);
    return () => window.clearInterval(timer);
  }, []);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  }, []);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Agents &amp; runs</CardTitle>
            <CardDescription>
              Background jobs launched from the operator console and dashboard actions —
              ingestion, deduplication, scout/research/verification agents, and article writing.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="size-3.5" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
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
            title="Failed to load agent runs"
            description={state.message}
          >
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="size-3.5" />
              Retry
            </Button>
          </EmptyState>
        )}

        {state.kind === "ok" && state.data.length === 0 && (
          <EmptyState
            icon={Bot}
            title="No agent runs yet"
            description="Launch an ingestion, dedup, scout, research, verification, or article run from the Stories or Sources pages and the activity will stream here."
          />
        )}

        {state.kind === "ok" && state.data.length > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-muted-foreground">{state.data.length} recent runs</p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="text-right">Job ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.data.map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell>
                      <span className="font-medium">{jobLabel(job.job_name)}</span>
                    </TableCell>
                    <TableCell>
                      <Badge className={JOB_STATUS_TONE[job.status]}>
                        {job.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(job.created_at)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(job.completed_at)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">
                      {job.job_id.slice(0, 8)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
