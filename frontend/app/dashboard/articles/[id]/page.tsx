"use client";

import * as React from "react";
import { ArrowLeft, Clock, ExternalLink, RefreshCw, Save } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Article, IngestionRunResponse, Story, StoryResearch } from "@/types";

const STATUS_TONE: Record<string, string> = {
  PUBLISHED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  APPROVED: "border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400",
  REVIEW: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  DRAFT: "border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400",
  REJECTED: "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
};

export default function ArticleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const articleId = Number(id);

  const [article, setArticle] = React.useState<Article | null>(null);
  const [story, setStory] = React.useState<Story | null>(null);
  const [research, setResearch] = React.useState<StoryResearch | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);
  const [saveMsg, setSaveMsg] = React.useState<string | null>(null);

  const [form, setForm] = React.useState({
    headline: "",
    subheadline: "",
    summary: "",
    body: "",
    seo_title: "",
    seo_description: "",
    status: "DRAFT",
  });

  React.useEffect(() => {
    if (Number.isNaN(articleId)) return;
    let cancelled = false;

    async function load() {
      try {
        const a = await apiGet<Article>(`/api/v1/articles/${articleId}`);
        if (cancelled) return;
        setArticle(a);
        setForm({
          headline: a.headline,
          subheadline: a.subheadline ?? "",
          summary: a.summary ?? "",
          body: a.body ?? "",
          seo_title: a.seo_title ?? "",
          seo_description: a.seo_description ?? "",
          status: a.status,
        });
        const [s, r] = await Promise.all([
          apiGet<Story>(`/api/v1/stories/${a.story_id}`).catch(() => null),
          apiGet<StoryResearch>(`/api/v1/research/runs/${a.story_id}`).catch(() => null),
        ]);
        if (!cancelled) {
          setStory(s);
          setResearch(r);
        }
        setLoading(false);
      } catch {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [articleId]);

  const handleSave = React.useCallback(async () => {
    setSaving(true);
    try {
      const updated = await apiPatch<Article>(`/api/v1/articles/${articleId}`, {
        headline: form.headline,
        subheadline: form.subheadline || null,
        summary: form.summary || null,
        body: form.body || null,
        seo_title: form.seo_title || null,
        seo_description: form.seo_description || null,
        status: form.status,
      });
      setArticle(updated);
      setSaveMsg("Saved");
      setTimeout(() => setSaveMsg(null), 2000);
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [articleId, form]);

  const handleRegenerate = React.useCallback(async () => {
    if (!article) return;
    setGenerating(true);
    try {
      await apiPost<IngestionRunResponse>(`/api/v1/articles/generate/stories/${article.story_id}`);
      setTimeout(() => {
        setGenerating(false);
        window.location.reload();
      }, 2500);
    } catch {
      setGenerating(false);
    }
  }, [article]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!article) {
    return (
      <EmptyState
        icon={ArrowLeft}
        title="Article not found"
        description="The article you're looking for doesn't exist."
      >
        <Link href="/dashboard/articles">
          <Button variant="outline" size="sm">
            <ArrowLeft className="size-3.5" />
            Back to articles
          </Button>
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <Link href="/dashboard/articles">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="size-3.5" />
          </Button>
        </Link>
        <div className="flex-1 space-y-1">
          <h1 className="text-lg font-semibold leading-tight">{article.headline}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge className={STATUS_TONE[article.status] ?? "border-zinc-400/40 bg-zinc-500/10 text-zinc-500"}>
              {article.status}
            </Badge>
            {story?.category && <Badge variant="outline">{story.category}</Badge>}
            <span className="inline-flex items-center gap-1">
              <Clock className="size-3" />
              Updated {new Date(article.updated_at).toLocaleString()}
            </span>
            {story?.url && (
              <a href={story.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">
                Original <ExternalLink className="size-3" />
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={generating}>
            <RefreshCw className={`size-3.5 ${generating ? "animate-spin" : ""}`} />
            {generating ? "Generating..." : "Regenerate"}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            <Save className="size-3.5" />
            {saving ? "Saving..." : saveMsg ?? "Save"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Edit draft</CardTitle>
              <CardDescription>
                Edits are saved to the database. Status changes drive the review pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground uppercase">Headline</label>
                <Input
                  value={form.headline}
                  onChange={(e) => setForm((f) => ({ ...f, headline: e.target.value }))}
                  maxLength={500}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground uppercase">Subheadline</label>
                <Input
                  value={form.subheadline}
                  onChange={(e) => setForm((f) => ({ ...f, subheadline: e.target.value }))}
                  maxLength={500}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground uppercase">Summary</label>
                <Textarea
                  value={form.summary}
                  onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                  rows={3}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground uppercase">Body (Markdown)</label>
                <Textarea
                  value={form.body}
                  onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
                  rows={16}
                  className="font-mono text-xs leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground uppercase">SEO Title</label>
                  <Input
                    value={form.seo_title}
                    onChange={(e) => setForm((f) => ({ ...f, seo_title: e.target.value }))}
                    maxLength={500}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground uppercase">SEO Description</label>
                  <Input
                    value={form.seo_description}
                    onChange={(e) => setForm((f) => ({ ...f, seo_description: e.target.value }))}
                    maxLength={1000}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground uppercase">Status</label>
                <Select value={form.status} onValueChange={(v) => setForm((f) => ({ ...f, status: v ?? "DRAFT" }))}>
                  <SelectTrigger className="w-full max-w-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DRAFT">DRAFT</SelectItem>
                    <SelectItem value="REVIEW">REVIEW</SelectItem>
                    <SelectItem value="APPROVED">APPROVED</SelectItem>
                    <SelectItem value="PUBLISHED">PUBLISHED</SelectItem>
                    <SelectItem value="REJECTED">REJECTED</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {saveMsg && <p className="text-sm text-muted-foreground">{saveMsg}</p>}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Story</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {story ? (
                <>
                  <p className="font-medium leading-snug">{story.title}</p>
                  <p className="text-xs text-muted-foreground line-clamp-3">{story.summary ?? "No story summary."}</p>
                  <div className="pt-1 text-xs text-muted-foreground">
                    ID #{story.id} · {story.category ?? "uncategorized"}
                  </div>
                </>
              ) : (
                <p className="text-muted-foreground">Story #{article.story_id}</p>
              )}
            </CardContent>
          </Card>

          {research && research.claims.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Verification ({research.claims.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {research.claims.map((claim) => (
                  <div key={claim.id} className="border rounded-md p-2 text-xs space-y-1">
                    <p className="leading-snug">{claim.claim_text}</p>
                    <div className="flex items-center gap-2">
                      <Badge variant={claim.status === "CONFIRMED" ? "default" : claim.status === "CONTRADICTED" ? "destructive" : "secondary"}>
                        {claim.status}
                      </Badge>
                      {claim.confidence_score !== null && (
                        <span className="text-muted-foreground">
                          {(claim.confidence_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {claim.evidences.length > 0 && (
                      <a
                        href={claim.evidences[0].url ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-muted-foreground hover:underline truncate w-full"
                      >
                        {claim.evidences[0].url ?? "evidence"} <ExternalLink className="size-2.5" />
                      </a>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}