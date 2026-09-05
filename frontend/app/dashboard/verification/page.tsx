"use client";

import * as React from "react";
import { AlertTriangle, RefreshCw, ShieldCheck } from "lucide-react";

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
import type { Story, ListResponse, DedupCandidate } from "@/types";

function scoreTone(score: number): string {
  if (score >= 0.8) return "text-emerald-600 dark:text-emerald-400 font-medium";
  if (score >= 0.5) return "text-amber-600 dark:text-amber-400 font-medium";
  return "text-muted-foreground";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function VerificationPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ListResponse<Story> }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [candidates, setCandidates] = React.useState<DedupCandidate[]>([]);
  const [tick, setTick] = React.useState(0);

  const load = React.useCallback(() => {
    let cancelled = false;
    Promise.all([
      apiGet<ListResponse<Story>>("/api/v1/stories?limit=100&status=VERIFICATION"),
      apiGet<DedupCandidate[]>("/api/v1/dedup/candidates?limit=20"),
    ])
      .then(([stories, cand]) => {
        if (!cancelled) {
          setCandidates(cand);
          setState({ kind: "ok", data: stories });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message:
              error instanceof Error ? error.message : "Failed to load verification queue.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => load(), [load, tick]);

  React.useEffect(() => {
    const timer = window.setInterval(() => setTick((t) => t + 1), 30000);
    return () => window.clearInterval(timer);
  }, []);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  }, []);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">Verification queue</CardTitle>
              <CardDescription>
                Stories in VERIFICATION are running claim checks against sources. Claims
                and evidence will surface here as the verification agent lands (Phase 7).
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
              title="Failed to load verification queue"
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
              icon={ShieldCheck}
              title="Nothing in verification right now"
              description="Stories enter VERIFICATION from the Story pipeline once research completes. The claim-checking agent (Phase 7) will populate claims and evidence here."
            />
          )}

          {state.kind === "ok" && state.data.items.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">{state.data.total} in verification</p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Story</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Confidence</TableHead>
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
                        <span className={scoreTone(story.confidence_score ?? 0)}>
                          {story.confidence_score !== null
                            ? `${(story.confidence_score * 100).toFixed(0)}%`
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Near-miss duplicates</CardTitle>
          <CardDescription>
            Potential duplicate stories detected by the dedup agent. Review and merge to
            keep the pipeline canonical.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {state.kind === "loading" && (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}
          {state.kind === "ok" && candidates.length === 0 && (
            <EmptyState
              icon={ShieldCheck}
              title="No near-miss pairs detected"
              description="Candidate duplicate pairs will appear here when the dedup agent flags stories that are similar but not identical."
            />
          )}
          {state.kind === "ok" && candidates.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">{candidates.length} candidate pair{candidates.length === 1 ? "" : "s"}</p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Story A</TableHead>
                    <TableHead>Story B</TableHead>
                    <TableHead className="text-right">Similarity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {candidates.map((cand, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{cand.title_a}</span>
                          <span className="text-xs text-muted-foreground">#{cand.story_id_a}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{cand.title_b}</span>
                          <span className="text-xs text-muted-foreground">#{cand.story_id_b}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={scoreTone(cand.score)}>
                          {(cand.score * 100).toFixed(0)}%
                        </span>
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
