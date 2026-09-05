import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm space-y-2">
          <p className="text-sm font-semibold tracking-tight">AI Newsroom</p>
          <p className="text-sm text-muted-foreground">
            An open pipeline for evidence-backed journalism — from RSS
            ingestion to human-approved publication.
          </p>
        </div>
        <nav className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          <div className="space-y-2 text-sm">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Newsroom
            </p>
            <Link
              href="/latest"
              className="block text-muted-foreground hover:text-foreground"
            >
              Latest
            </Link>
            <Link
              href="/search"
              className="block text-muted-foreground hover:text-foreground"
            >
              Search
            </Link>
          </div>
          <div className="space-y-2 text-sm">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Project
            </p>
            <Link
              href="/about"
              className="block text-muted-foreground hover:text-foreground"
            >
              About
            </Link>
            <Link
              href="/dashboard"
              className="block text-muted-foreground hover:text-foreground"
            >
              Dashboard
            </Link>
          </div>
          <div className="space-y-2 text-sm">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Pipeline
            </p>
            <span className="block text-muted-foreground">Ingest</span>
            <span className="block text-muted-foreground">Research</span>
            <span className="block text-muted-foreground">Verify</span>
            <span className="block text-muted-foreground">Publish</span>
          </div>
        </nav>
      </div>
      <div className="border-t">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 text-xs text-muted-foreground sm:px-6">
          <p>© {new Date().getFullYear()} AI Newsroom</p>
          <p>Evidence-backed by design.</p>
        </div>
      </div>
    </footer>
  );
}