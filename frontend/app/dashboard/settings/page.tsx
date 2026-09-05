import { Settings } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function SettingsPage() {
  return (
    <SectionShell
      icon={Settings}
      title="Settings"
      description="Newsroom-wide configuration: pipeline behaviour, defaults, and operator preferences."
      emptyTitle="Configuration coming soon"
      emptyDescription="Settings for ingestion cadence, verification thresholds, and publishing defaults will live here as the backend exposes them."
    />
  );
}