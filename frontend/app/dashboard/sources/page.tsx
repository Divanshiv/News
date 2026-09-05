import { Rss } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function SourcesPage() {
  return (
    <SectionShell
      icon={Rss}
      title="Sources"
      description="Manage the RSS feeds and registered outlets that feed the ingestion stage. Source health and output volume are tracked here."
      emptyTitle="No sources configured"
      emptyDescription="RSS feeds and sources will be registered here and passed to the ingestion pipeline. Source status and last-fetch times will be shown."
    />
  );
}