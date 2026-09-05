import type { Metadata } from "next";
import { Inbox } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PublicPageShell } from "@/components/public-page-shell";

export const metadata: Metadata = {
  title: "Latest",
  description:
    "The most recent stories published by the AI Newsroom pipeline.",
};

export default function LatestPage() {
  return (
    <PublicPageShell
      eyebrow="Despatch"
      title="Latest"
      description="Published stories from the newsroom pipeline, newest first."
    >
      <EmptyState
        icon={Inbox}
        title="No stories published yet"
        description="Stories will appear here after ingestion, research, verification, drafting, and human approval have completed."
      />
    </PublicPageShell>
  );
}