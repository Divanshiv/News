import { Bot } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function AgentsPage() {
  return (
    <SectionShell
      icon={Bot}
      title="Agents"
      description="Configure and monitor the agents that run the pipeline — ingestion, research, verification, writing, and social preparation."
      emptyTitle="No agents registered"
      emptyDescription="Pipeline agents will be listed here with their status, configuration, and recent runs once the backend is wired up."
    />
  );
}