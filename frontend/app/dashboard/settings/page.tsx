"use client";

import * as React from "react";
import { AlertTriangle, RefreshCw, Settings } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { apiGet } from "@/lib/api";
import type { ServiceConfig } from "@/types";

type RowProps = { label: string; value: string; mono?: boolean };

function Row({ label, value, mono }: RowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [state, setState] = React.useState<
    | { kind: "loading" }
    | { kind: "ok"; data: ServiceConfig }
    | { kind: "error"; message: string }
  >({ kind: "loading" });
  const [tick, setTick] = React.useState(0);

  const load = React.useCallback(() => {
    let cancelled = false;
    apiGet<ServiceConfig>("/api/v1/meta/config")
      .then((data) => {
        if (!cancelled) setState({ kind: "ok", data });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setState({
            kind: "error",
            message:
              error instanceof Error ? error.message : "Failed to load configuration.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => load(), [load, tick]);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  }, []);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Settings</CardTitle>
            <CardDescription>
              Live service configuration. Values are read from the backend environment and are
              read-only here for now.
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
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        )}

        {state.kind === "error" && (
          <EmptyState
            icon={AlertTriangle}
            title="Failed to load configuration"
            description={state.message}
          >
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="size-3.5" />
              Retry
            </Button>
          </EmptyState>
        )}

        {state.kind === "ok" && (
          <div className="flex flex-col gap-3">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Service
                </h3>
                <div className="divide-y divide-border rounded-lg border px-4">
                  <Row label="Name" value={state.data.app_name} />
                  <Row label="Version" value={state.data.app_version} mono />
                  <div className="flex items-center justify-between gap-4 py-2">
                    <span className="text-sm text-muted-foreground">Environment</span>
                    <Badge
                      className={
                        state.data.environment === "production"
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400"
                      }
                    >
                      {state.data.environment}
                    </Badge>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  LLM provider
                </h3>
                <div className="divide-y divide-border rounded-lg border px-4">
                  <Row label="Provider" value={state.data.llm_provider} mono />
                  <Row label="Model" value={state.data.ollama_model} mono />
                  <Row label="Base URL" value={state.data.ollama_url} mono />
                </div>
              </div>
            </div>

            <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Settings className="size-3.5" />
              Editable settings for ingestion cadence, verification thresholds, and publishing
              defaults arrive as the related pipeline phases land.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
