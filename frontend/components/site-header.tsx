import Link from "next/link";
import { Newspaper } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/latest", label: "Latest" },
  { href: "/search", label: "Search" },
  { href: "/about", label: "About" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold tracking-tight"
        >
          <span className="flex size-7 items-center justify-center rounded-md bg-foreground text-background">
            <Newspaper className="size-4" />
          </span>
          <span className="hidden sm:inline">AI Newsroom</span>
          <span className="text-[0.65rem] font-normal uppercase tracking-widest text-muted-foreground sm:ml-1">
            Despatch
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {link.label}
            </Link>
          ))}
          <div className="mx-1 h-4 w-px bg-border" aria-hidden />
          <Link
            href="/dashboard"
            className={cn(buttonVariants({ variant: "default", size: "sm" }))}
          >
            Operator Console
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}