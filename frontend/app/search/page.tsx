import type { Metadata } from "next";
import { SearchX } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PublicPageShell } from "@/components/public-page-shell";
import { SearchForm } from "@/components/search-form";

export const metadata: Metadata = {
  title: "Search",
  description: "Search the archive of published, human-approved stories.",
};

type SearchPageProps = {
  searchParams: Promise<{ q?: string | string[] }>;
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const { q } = await searchParams;
  const query = typeof q === "string" ? q.trim() : "";

  return (
    <PublicPageShell
      eyebrow="Archive"
      title="Search"
      description="Search published stories across the newsroom archive."
    >
      <SearchForm initialQuery={query} />
      <div className="mt-10">
        <EmptyState
          icon={SearchX}
          title={query ? `No results for “${query}”` : "Search the archive"}
          description={
            query
              ? "No published stories match that query yet. Try a broader term."
              : "Enter a query above to search published, human-approved stories."
          }
        />
      </div>
    </PublicPageShell>
  );
}