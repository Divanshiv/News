"use client";

import * as React from "react";
import { AlertTriangle, FileText, RefreshCw } from "lucide-react";

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
import type { Article, ListResponse } from "@/types";

const STATUS_TONE: Record<string, string> = {
  PUBLISHED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  APPROVED: "border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400",
  REVIEW: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  DRAFT: "border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400",
  REJECTED: "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
};

export default function ArticlesPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ListResponse<Article> }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [tick, setTick] = React.useState(0);

  const load = React.useCallback(() => {
    let cancelled = false;
    apiGet<ListResponse<Article>>("/api/v1/articles?limit=100")
      .then((data) => {
        if (!cancelled) setState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Failed to load articles.",
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
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Articles</CardTitle>
            <CardDescription>
              Drafts produced from verified research, ready for editing and approval. Nothing
              here is published without sign-off.
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
            title="Failed to load articles"
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
            icon={FileText}
            title="No articles yet"
            description="Article drafts will appear here as verified stories move into the writing stage. Editors will review, revise, and approve or reject each one."
          />
        )}

        {state.kind === "ok" && state.data.items.length > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-muted-foreground">{state.data.total} articles</p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Headline</TableHead>
                  <TableHead>Story</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.data.items.map((article) => (
                  <TableRow key={article.id}>
                    <TableCell className="max-w-md">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium">{article.headline}</span>
                        {article.subheadline && (
                          <span className="text-xs text-muted-foreground line-clamp-1">
                            {article.subheadline}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">#{article.story_id}</span>
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_TONE[article.status] ?? "border-zinc-400/40 bg-zinc-500/10 text-zinc-500"}>
                        {article.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground whitespace-nowrap">
                      {article.published_at
                        ? new Date(article.published_at).toLocaleString()
                        : new Date(article.updated_at).toLocaleString()}
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
