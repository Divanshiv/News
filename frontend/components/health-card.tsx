"use client";

import * as React from "react";
import { Database, RefreshCw, Server } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet } from "@/lib/api";

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: string;
  timestamp: string;
};

type HealthCardState =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "degraded"; data: HealthResponse }
  | { kind: "error"; message: string };

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

function statusBadge(status: string): React.ReactNode {
  if (status === "ok") {
    return (
      <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        ok
      </Badge>
    );
  }
  return (
    <Badge className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400">
      degraded
    </Badge>
  );
}

function databaseBadge(database: string): React.ReactNode {
  if (database === "connected") {
    return (
      <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        connected
      </Badge>
    );
  }
  return (
    <Badge className="border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400">
      unavailable
    </Badge>
  );
}

export function HealthCard() {
  const [state, setState] = React.useState<HealthCardState>({
    kind: "loading",
  });

  const [refreshIndex, setRefreshIndex] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    apiGet<HealthResponse>("/api/v1/health")
      .then((data) => {
        if (!cancelled) {
          setState({
            kind: data.status === "ok" ? "ok" : "degraded",
            data,
          });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Backend health check failed.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refreshIndex]);

  const refresh = React.useCallback(() => {
    setState({ kind: "loading" });
    setRefreshIndex((index) => index + 1);
  }, []);

  const interactive = (content: React.ReactNode, error = false) => (
    <div className="flex flex-col">
      <div className={error ? "text-sm text-muted-foreground" : ""}>
        {content}
      </div>
      <div className="mt-4 flex items-center justify-between border-t pt-3">
        <p className="text-xs text-muted-foreground">
          {state.kind === "loading"
            ? "Checking backend…"
            : state.kind === "error"
              ? "Backend unreachable"
              : `Reporting ${state.data.service}`}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={refresh}
          disabled={state.kind === "loading"}
        >
          <RefreshCw
            className={state.kind === "loading" ? "animate-spin" : undefined}
          />
          Refresh
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-1">
      {state.kind === "loading" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-5 w-24" />
          </div>
          <div className="space-y-2">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-4 w-full max-w-60" />
            ))}
          </div>
        </div>
      )}

      {state.kind === "error" &&
        interactive(
          <div className="flex items-start gap-3">
            <Server className="mt-0.5 size-4 shrink-0 text-destructive" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">Backend offline</p>
                <Badge className="border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400">
                  unavailable
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{state.message}</p>
            </div>
          </div>,
        )}

      {(state.kind === "ok" || state.kind === "degraded") &&
        interactive(
          <div className="space-y-2.5">
            <div className="flex items-center gap-2">
              <Server className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium">Backend status</span>
              {statusBadge(state.data.status)}
            </div>
            <div className="flex items-center gap-2">
              <Database className="size-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Database</span>
              {databaseBadge(state.data.database)}
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 pt-1 text-xs sm:grid-cols-4">
              <div>
                <dt className="text-muted-foreground">Service</dt>
                <dd className="mt-0.5 font-medium">{state.data.service}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Version</dt>
                <dd className="mt-0.5 font-medium">{state.data.version}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Environment</dt>
                <dd className="mt-0.5 font-medium">{state.data.environment}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Timestamp</dt>
                <dd className="mt-0.5 font-medium">
                  {formatTimestamp(state.data.timestamp)}
                </dd>
              </div>
            </dl>
          </div>,
        )}
    </div>
  );
}