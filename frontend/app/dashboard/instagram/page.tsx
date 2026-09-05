import { Camera } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function InstagramPage() {
  return (
    <SectionShell
      icon={Camera}
      title="Instagram"
      description="Repurposed editorial content prepared for Instagram — card layouts, captions, and post schedules derived from approved articles."
      emptyTitle="No Instagram content yet"
      emptyDescription="Instagram posts derived from approved articles will be generated and staged here for review before any post goes live."
    />
  );
}