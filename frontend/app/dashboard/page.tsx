import { HealthCard } from "@/components/health-card";
import { OverviewStats } from "@/components/dashboard/overview-stats";
import {
  StatusBadge,
  STORY_STATUSES,
  type StoryStatus,
} from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
          <OverviewStats />

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

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <HealthCard />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}