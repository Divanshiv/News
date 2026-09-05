import { Send } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function PublishingPage() {
  return (
    <SectionShell
      icon={Send}
      title="Publishing"
      description="Schedule and manage approved content as it ships to the public site and distribution channels."
      emptyTitle="Nothing scheduled for publication"
      emptyDescription="Approved articles and Instagram posts will be queued here for publication, with timestamps for when they go live."
    />
  );
}