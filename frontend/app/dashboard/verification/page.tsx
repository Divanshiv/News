"use client";

import * as React from "react";
import { AlertTriangle, RefreshCw, ShieldCheck, Play } from "lucide-react";

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

interface ClaimData {
  id: number;
  claim_text: string;
  status: string;
  confidence_score: number | null;
  evidences: { id: number; evidence_text: string; url: string | null; source_id: number | null }[];
}

interface VerificationData {
  story_id: number;
  title: string;
  claims: ClaimData[];
  overall_confidence: number;
  verification_summary: string;
}

function ClaimStatusBadge({ status }: { status: string }) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    CONFIRMED: "default",
    LIKELY: "secondary",
    UNCONFIRMED: "outline",
    CONTRADICTED: "destructive",
  };
  return <Badge variant={variants[status] ?? "outline"}>{status}</Badge>;
}

export default function VerificationPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ListResponse<Story> }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [candidates, setCandidates] = React.useState<DedupCandidate[]>([]);
  const [tick, setTick] = React.useState(0);
  const [selectedStory, setSelectedStory] = React.useState<number | null>(null);
  const [verification, setVerification] = React.useState<VerificationData | null>(null);
  const [verifying, setVerifying] = React.useState(false);

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

  const loadVerification = React.useCallback(async (storyId: number) => {
    setSelectedStory(storyId);
    try {
      const data = await apiGet<VerificationData>(`/api/v1/verification/stories/${storyId}`);
      setVerification(data);
    } catch {
      setVerification(null);
    }
  }, []);

  const runVerification = React.useCallback(async () => {
    setVerifying(true);
    try {
      await apiPost("/api/v1/verification/run");
      setTimeout(() => {
        setVerifying(false);
        refresh();
      }, 2000);
    } catch {
      setVerifying(false);
    }
  }, [refresh]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="text-base">Verification queue</CardTitle>
              <CardDescription>
                Stories ready for claim verification. Run the verification agent to check
                claims against evidence and determine confidence levels.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={runVerification} disabled={verifying}>
                <Play className="size-3.5" />
                {verifying ? "Running..." : "Run verification"}
              </Button>
              <Button variant="outline" size="sm" onClick={refresh}>
                <RefreshCw className="size-3.5" />
                Refresh
              </Button>
            </div>
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
              description="Stories enter VERIFICATION from the Story pipeline once research completes."
            />
          )}

          {state.kind === "ok" && state.data.items.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">{state.data.total} in verification</p>
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50%]">Story</TableHead>
                    <TableHead className="w-[15%]">Category</TableHead>
                    <TableHead className="w-[13%]">Confidence</TableHead>
                    <TableHead className="w-[12%]">Status</TableHead>
                    <TableHead className="w-[10%] text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {state.data.items.map((story) => (
                    <TableRow key={story.id}>
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
                        <span className={scoreTone(story.confidence_score ?? 0)}>
                          {story.confidence_score !== null
                            ? `${(story.confidence_score * 100).toFixed(0)}%`
                            : "—"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={story.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => loadVerification(story.id)}
                        >
                          View claims
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedStory && verification && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Claims — {verification.title}</CardTitle>
            <CardDescription>
              {verification.verification_summary} Overall confidence:{" "}
              {(verification.overall_confidence * 100).toFixed(0)}%
            </CardDescription>
          </CardHeader>
          <CardContent>
            {verification.claims.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title="No claims extracted"
                description="Run research first to extract claims from sources."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Claim</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Evidence</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {verification.claims.map((claim) => (
                    <TableRow key={claim.id}>
                      <TableCell className="max-w-md">{claim.claim_text}</TableCell>
                      <TableCell>
                        <ClaimStatusBadge status={claim.status} />
                      </TableCell>
                      <TableCell>
                        <span className={scoreTone(claim.confidence_score ?? 0)}>
                          {claim.confidence_score !== null
                            ? `${(claim.confidence_score * 100).toFixed(0)}%`
                            : "—"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground">
                          {claim.evidences.length} source{claim.evidences.length === 1 ? "" : "s"}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

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
