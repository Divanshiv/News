"use client";

import * as React from "react";
import { AlertTriangle, RefreshCw, Telescope } from "lucide-react";

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
import { apiGet } from "@/lib/api";
import type { Story, ListResponse } from "@/types";

const POLL_INTERVAL = 30000;

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

export default function ResearchPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ListResponse<Story> }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [tick, setTick] = React.useState(0);

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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Research queue</CardTitle>
            <CardDescription>
              Stories actively being researched by agents (status RESEARCHING). Research
              runs assemble background, context, and corroborating references before any
              claim is written.
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Story</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Importance</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Discovered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.data.items.map((story) => (
                  <TableRow key={story.id}>
                    <TableCell>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium">{story.title}</span>
                        {story.scout_reason && (
                          <span className="text-xs text-muted-foreground">
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
          </div>
        )}
      </CardContent>
    </Card>
  );
}
