"use client";

import * as React from "react";
import { ArrowLeft, ExternalLink, PenLine, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";

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
import type { Story, StoryResearch, IngestionRunResponse, Article } from "@/types";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function scoreTone(score: number): string {
  if (score >= 0.8) return "text-emerald-600 dark:text-emerald-400 font-medium";
  if (score >= 0.5) return "text-amber-600 dark:text-amber-400 font-medium";
  return "text-muted-foreground";
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

export default function StoryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const storyId = Number(id);
  const [story, setStory] = React.useState<Story | null>(null);
  const [research, setResearch] = React.useState<StoryResearch | null>(null);
  const [article, setArticle] = React.useState<Article | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [researching, setResearching] = React.useState(false);
  const [verifying, setVerifying] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);

  React.useEffect(() => {
    if (Number.isNaN(storyId)) return;
    let cancelled = false;
    Promise.all([
      apiGet<Story>(`/api/v1/stories/${storyId}`),
      apiGet<StoryResearch>(`/api/v1/research/runs/${storyId}`).catch(() => null),
      apiGet<Article>(`/api/v1/articles/by-story/${storyId}`).catch(() => null),
    ]).then(([s, r, a]) => {
      if (!cancelled) {
        setStory(s);
        setResearch(r);
        setArticle(a);
        setLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [storyId]);

  const handleRunResearch = React.useCallback(async () => {
    setResearching(true);
    try {
      await apiPost<IngestionRunResponse>(`/api/v1/research/stories/${storyId}`);
      setTimeout(() => {
        setResearching(false);
        window.location.reload();
      }, 2000);
    } catch {
      setResearching(false);
    }
  }, [storyId]);

  const handleRunVerification = React.useCallback(async () => {
    setVerifying(true);
    try {
      await apiPost<IngestionRunResponse>(`/api/v1/verification/stories/${storyId}`);
      setTimeout(() => {
        setVerifying(false);
        window.location.reload();
      }, 2000);
    } catch {
      setVerifying(false);
    }
  }, [storyId]);

  const handleGenerateArticle = React.useCallback(async () => {
    setGenerating(true);
    try {
      await apiPost<IngestionRunResponse>(`/api/v1/articles/generate/stories/${storyId}`);
      setTimeout(() => {
        setGenerating(false);
        window.location.reload();
      }, 2500);
    } catch {
      setGenerating(false);
    }
  }, [storyId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!story) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="Story not found"
        description="The story you're looking for doesn't exist."
      >
        <Link href="/dashboard/stories">
          <Button variant="outline" size="sm">
            <ArrowLeft className="size-3.5" />
            Back to stories
          </Button>
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/stories">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="size-3.5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-semibold">{story.title}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <StatusBadge status={story.status} />
            {story.category && <Badge variant="outline">{story.category}</Badge>}
            {story.url && (
              <a href={story.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">
                Original <ExternalLink className="size-3" />
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRunResearch} disabled={researching}>
            <RefreshCw className={`size-3.5 ${researching ? "animate-spin" : ""}`} />
            {researching ? "Researching..." : "Run research"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleRunVerification} disabled={verifying}>
            <RefreshCw className={`size-3.5 ${verifying ? "animate-spin" : ""}`} />
            {verifying ? "Verifying..." : "Run verification"}
          </Button>
          {!article && (
            <Button variant="outline" size="sm" onClick={handleGenerateArticle} disabled={generating}>
              <PenLine className={`size-3.5 ${generating ? "animate-spin" : ""}`} />
              {generating ? "Generating..." : "Generate article"}
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Story Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {story.summary ? (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Summary (from RSS feed)</h3>
              <p className="text-sm leading-relaxed">{story.summary}</p>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground italic">
              No summary available from the RSS feed.
            </div>
          )}
          {story.url && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Original Article</h3>
              <a
                href={story.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline break-all"
              >
                {story.url}
              </a>
            </div>
          )}
          {story.author && (
            <div className="text-sm">
              <span className="text-muted-foreground">Author: </span>
              {story.author}
            </div>
          )}
          {story.image_url && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Image</h3>
              <img
                src={story.image_url}
                alt={story.title}
                className="max-w-md rounded-lg border"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Importance</span>
              <p className="font-medium">
                {story.importance_score !== null ? `${story.importance_score}/10` : "—"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Confidence</span>
              <p className={`font-medium ${scoreTone(story.confidence_score ?? 0)}`}>
                {story.confidence_score !== null ? `${(story.confidence_score * 100).toFixed(0)}%` : "—"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Research</span>
              <p className="font-medium">{story.should_research ? "Yes" : "No"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Discovered</span>
              <p className="font-medium">{formatDate(story.discovered_at)}</p>
            </div>
          </div>
          {story.scout_reason && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Scout Reason</h3>
              <p className="text-sm">{story.scout_reason}</p>
            </div>
          )}
          {story.source_names.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Sources</h3>
              <div className="flex flex-wrap gap-1">
                {story.source_names.map((name) => (
                  <Badge key={name} variant="secondary">{name}</Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {article && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Article</CardTitle>
            <CardDescription>
              Generated article draft. Status: {article.status}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {article.subheadline && (
              <p className="text-sm text-muted-foreground">{article.subheadline}</p>
            )}
            {article.summary && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Summary</h3>
                <p className="text-sm">{article.summary}</p>
              </div>
            )}
            {article.body && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Body</h3>
                <div className="text-sm whitespace-pre-wrap max-h-96 overflow-y-auto border rounded-lg p-4">
                  {article.body}
                </div>
              </div>
            )}
            {article.seo_title && (
              <div className="text-xs text-muted-foreground">
                SEO Title: {article.seo_title}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!article && (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              icon={ShieldCheck}
              title="No article yet"
              description="Generate an article draft from this story's verified research and claims."
            >
              <Button variant="outline" size="sm" onClick={handleGenerateArticle} disabled={generating}>
                <PenLine className={`size-3.5 ${generating ? "animate-spin" : ""}`} />
                {generating ? "Generating..." : "Generate article"}
              </Button>
            </EmptyState>
          </CardContent>
        </Card>
      )}

      {research && research.claims.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Claims ({research.claims.length})</CardTitle>
            <CardDescription>
              Claims extracted during research. Run verification to check status.
            </CardDescription>
          </CardHeader>
          <CardContent>
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
                {research.claims.map((claim) => (
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
          </CardContent>
        </Card>
      )}

      {research && research.sources.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Research Sources ({research.sources.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Relationship</TableHead>
                  <TableHead className="text-right">Relevance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {research.sources.map((source) => (
                  <TableRow key={source.source_id}>
                    <TableCell>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium">{source.name || "Unknown"}</span>
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-muted-foreground hover:underline truncate max-w-md"
                          >
                            {source.url}
                          </a>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{source.relationship}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {source.relevance_score !== null ? (
                        <span className={scoreTone(source.relevance_score)}>
                          {(source.relevance_score * 100).toFixed(0)}%
                        </span>
                      ) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {research && research.runs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Research Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {research.runs.map((run) => (
                  <TableRow key={run.id}>
                    <TableCell>{run.agent_name}</TableCell>
                    <TableCell>
                      <Badge variant={run.status === "COMPLETED" ? "default" : "secondary"}>
                        {run.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">{formatDate(run.started_at)}</TableCell>
                    <TableCell className="text-xs">{formatDate(run.completed_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {!research && (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              icon={ShieldCheck}
              title="No research data yet"
              description="Run research to gather sources and extract claims for this story."
            >
              <Button variant="outline" size="sm" onClick={handleRunResearch} disabled={researching}>
                <RefreshCw className={`size-3.5 ${researching ? "animate-spin" : ""}`} />
                {researching ? "Researching..." : "Run research"}
              </Button>
            </EmptyState>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
