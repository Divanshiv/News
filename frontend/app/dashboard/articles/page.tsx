import { FileText } from "lucide-react";

import { SectionShell } from "@/components/dashboard/section-shell";

export default function ArticlesPage() {
  return (
    <SectionShell
      icon={FileText}
      title="Articles"
      description="Drafts produced from verified research, ready for human editing and approval. Nothing here is published without sign-off."
      emptyTitle="No drafts yet"
      emptyDescription="Article drafts will appear here as verified stories move into the writing stage. Editors will review, revise, and approve or reject each one."
    />
  );
}