import type { Metadata } from "next";
import { FileQuestion } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PublicPageShell } from "@/components/public-page-shell";

type ArticlePageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({
  params,
}: ArticlePageProps): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: slug.split("-").slice(0, 5).join(" "),
    description: "A single story in the AI Newsroom archive.",
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  return (
    <PublicPageShell
      eyebrow="Article"
      title="Article"
      description="A published story from the AI Newsroom archive."
    >
      <EmptyState
        icon={FileQuestion}
        title="This article is not available yet"
        description={`The article at "${slug}" has not been published. Stories only appear here after research, verification, and human approval are complete.`}
      />
    </PublicPageShell>
  );
}