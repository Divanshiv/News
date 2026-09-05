import type { Metadata } from "next";
import { FolderOpen } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PublicPageShell } from "@/components/public-page-shell";

function humanize(slug: string): string {
  return slug
    .split(/[-_]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

type CategoryPageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({
  params,
}: CategoryPageProps): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: `${humanize(slug)}`,
    description: `Stories filed under ${humanize(slug)} in the AI Newsroom.`,
  };
}

export default async function CategoryPage({ params }: CategoryPageProps) {
  const { slug } = await params;
  return (
    <PublicPageShell
      eyebrow="Section"
      title={humanize(slug)}
      description={`Stories filed under ${humanize(slug)}, drawn from the newsroom source taxonomy and awaiting human approval before publication.`}
    >
      <EmptyState
        icon={FolderOpen}
        title="No stories in this section yet"
        description="Once the pipeline ingests and approves stories tagged with this section, they will be listed here."
      />
    </PublicPageShell>
  );
}