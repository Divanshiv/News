"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SearchForm({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();
  const [query, setQuery] = React.useState(initialQuery);

  return (
    <form
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmed = query.trim();
        router.push(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
      }}
      className="flex w-full max-w-xl items-center gap-2"
    >
      <Input
        aria-label="Search published stories"
        placeholder="Search the archive…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="h-9"
      />
      <Button type="submit" size="sm" className="shrink-0 gap-1.5">
        <Search className="size-3.5" />
        Search
      </Button>
    </form>
  );
}