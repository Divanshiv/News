import type { LucideIcon } from "lucide-react";
import {
  Activity,
  FileCheck,
  Inbox,
  Send,
  ShieldAlert,
  Telescope,
  XCircle,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { HealthCard } from "@/components/health-card";
import {
  StatusBadge,
  STORY_STATUSES,
  type StoryStatus,
} from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type StatCardProps = {
  icon: LucideIcon;
  label: string;
  hint: string;
  href: string;
};

function StatCard({ icon: Icon, label, hint, href }: StatCardProps) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-3 rounded-xl border bg-card p-4 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring hover:border-foreground/15"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          {label}
        </span>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tracking-tight tabular-nums">
          0
        </span>
        <span className="text-xs text-muted-foreground">{hint}</span>
      </div>
    </Link>
  );
}

const STAT_CARDS: StatCardProps[] = [
  {
    icon: Inbox,
    label: "New Stories",
    hint: "awaits triage",
    href: "/dashboard/stories",
  },
  {
    icon: Telescope,
    label: "Researching",
    hint: "agents active",
    href: "/dashboard/research",
  },
  {
    icon: ShieldAlert,
    label: "Needs Verification",
    hint: "in claim check",
    href: "/dashboard/verification",
  },
  {
    icon: FileCheck,
    label: "Ready for Review",
    hint: "await sign-off",
    href: "/dashboard/articles",
  },
  {
    icon: Send,
    label: "Published",
    hint: "live on site",
    href: "/dashboard/publishing",
  },
  {
    icon: XCircle,
    label: "Rejected",
    hint: "flagged by editors",
    href: "/dashboard/stories",
  },
];

const STATUS_NOTES: Record<StoryStatus, string> = {
  DISCOVERED: "Ingested, awaiting triage",
  RESEARCHING: "Agents gathering context",
  VERIFICATION: "Claims being checked",
  DRAFT: "Article drafted from research",
  REVIEW: "Human review pending",
  APPROVED: "Signed off for release",
  PUBLISHED: "Live on the public site",
  REJECTED: "Flagged, not publishable",
  MERGED: "Absorbed into a canonical story",
};

export default function OverviewPage() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {STAT_CARDS.map((card) => (
              <StatCard
                key={card.label}
                icon={card.icon}
                label={card.label}
                hint={card.hint}
                href={card.href}
              />
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={Activity}
                title="No pipeline activity yet"
                description="Agent events, ingest runs, and approval actions will stream here once the pipeline begins processing stories."
              />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <HealthCard />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pipeline</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2.5">
                {STORY_STATUSES.map((status) => (
                  <li
                    key={status}
                    className="flex items-center justify-between gap-3"
                  >
                    <StatusBadge status={status} />
                    <span className="text-xs text-muted-foreground">
                      {STATUS_NOTES[status]}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}