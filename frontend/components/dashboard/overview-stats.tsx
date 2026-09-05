"use client";

import * as React from "react";
import { Activity, FileCheck, Inbox, Send, ShieldAlert, Telescope, XCircle } from "lucide-react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { apiGet } from "@/lib/api";
import type { ListResponse, Story } from "@/types";
import type { LucideIcon } from "lucide-react";

type StatCardProps = {
  icon: LucideIcon;
  label: string;
  hint: string;
  href: string;
  value: number | null;
  loading: boolean;
};

function StatCard({ icon: Icon, label, hint, href, value, loading }: StatCardProps) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-3 rounded-xl border bg-card p-4 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring hover:border-foreground/15"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <div className="flex items-baseline gap-1.5">
        {loading ? (
          <span className="h-7 w-8 animate-pulse rounded bg-muted" />
        ) : (
          <span className="text-2xl font-semibold tracking-tight tabular-nums">
            {value ?? "—"}
          </span>
        )}
        <span className="text-xs text-muted-foreground">{hint}</span>
      </div>
    </Link>
  );
}

type OverviewStatsState = {
  loading: boolean;
  discovered: number;
  researching: number;
  verification: number;
  review: number;
  published: number;
  rejected: number;
};

export function OverviewStats() {
  const [state, setState] = React.useState<OverviewStatsState>({
    loading: true,
    discovered: 0,
    researching: 0,
    verification: 0,
    review: 0,
    published: 0,
    rejected: 0,
  });

  const [tick, setTick] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    const counts: Record<string, number> = {};
    const statuses = ["DISCOVERED", "RESEARCHING", "VERIFICATION", "REVIEW", "PUBLISHED", "REJECTED"];

    Promise.all(
      statuses.map((status) =>
        apiGet<ListResponse<Story>>(`/api/v1/stories?limit=1&status=${status}`)
          .then((data) => {
            counts[status] = data.total;
          })
          .catch(() => {
            counts[status] = 0;
          }),
      ),
    ).finally(() => {
      if (!cancelled) {
        setState({
          loading: false,
          discovered: counts["DISCOVERED"] ?? 0,
          researching: counts["RESEARCHING"] ?? 0,
          verification: counts["VERIFICATION"] ?? 0,
          review: counts["REVIEW"] ?? 0,
          published: counts["PUBLISHED"] ?? 0,
          rejected: counts["REJECTED"] ?? 0,
        });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  React.useEffect(() => {
    const timer = window.setInterval(() => setTick((t) => t + 1), 30000);
    return () => window.clearInterval(timer);
  }, []);

  const done = !state.loading;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Activity</CardTitle>
          <button
            onClick={() => {
              setState((s) => ({ ...s, loading: true }));
              setTick((t) => t + 1);
            }}
            className="text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            Refresh
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {done && !state.discovered && !state.researching && !state.verification && !state.review && !state.published && !state.rejected ? (
          <EmptyState
            icon={Activity}
            title="No pipeline activity yet"
            description="Agent events, ingest runs, and approval actions will stream here once the pipeline begins processing stories."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard icon={Inbox} label="New Stories" hint="awaits triage" href="/dashboard/stories" value={state.discovered} loading={!done} />
            <StatCard icon={Telescope} label="Researching" hint="agents active" href="/dashboard/research" value={state.researching} loading={!done} />
            <StatCard icon={ShieldAlert} label="Needs Verification" hint="in claim check" href="/dashboard/verification" value={state.verification} loading={!done} />
            <StatCard icon={FileCheck} label="Ready for Review" hint="await sign-off" href="/dashboard/articles" value={state.review} loading={!done} />
            <StatCard icon={Send} label="Published" hint="live on site" href="/dashboard/publishing" value={state.published} loading={!done} />
            <StatCard icon={XCircle} label="Rejected" hint="flagged by editors" href="/dashboard/stories" value={state.rejected} loading={!done} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
