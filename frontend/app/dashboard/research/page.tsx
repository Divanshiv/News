import { Telescope } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function ResearchPage() {
  return (
    <SectionShell
      icon={Telescope}
      title="Research"
      description="Automated research agents gather background, context, and corroborating references for each story before any claim is written down."
      emptyTitle="No research runs yet"
      emptyDescription="Research assignments will queue here as stories are triaged. Each run will assemble source material and citations for the verification stage."
    />
  );
}