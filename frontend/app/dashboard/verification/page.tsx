import { ShieldCheck } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function VerificationPage() {
  return (
    <SectionShell
      icon={ShieldCheck}
      title="Verification"
      description="The editorial gate where every claim is checked against its sources. Unverifiable assertions are flagged here and never reach a draft."
      emptyTitle="No claims awaiting verification"
      emptyDescription="Claims requiring verification will surface here once research completes. Each item tracks its check status and cited sources."
    />
  );
}