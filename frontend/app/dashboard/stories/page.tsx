import { Newspaper } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function StoriesPage() {
  return (
    <SectionShell
      icon={Newspaper}
      title="Stories"
      description="Raw stories ingested from RSS feeds and registered sources, awaiting triage before they enter the research and verification pipeline."
      emptyTitle="No stories ingested yet"
      emptyDescription="Stories will appear here after source ingestion begins. Each item starts in the DISCOVERED state and moves through research, verification, drafting, and review."
    />
  );
}