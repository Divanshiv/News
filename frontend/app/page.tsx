import Link from "next/link";
import {
  ArrowRight,
  FileText,
  Newspaper,
  Rss,
  SearchCheck,
  Send,
  ShieldCheck,
} from "lucide-react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PIPELINE_STEPS = [
  {
    icon: Rss,
    title: "Ingest",
    description:
      "RSS feeds and sources are pulled continuously into the newsroom queue.",
  },
  {
    icon: SearchCheck,
    title: "Research",
    description:
      "Agents gather background, context, and corroborating references for every story.",
  },
  {
    icon: ShieldCheck,
    title: "Verify",
    description:
      "Claims are checked against sources before a word is written.",
  },
  {
    icon: FileText,
    title: "Write",
    description:
      "Drafts are produced from verified research, citing what was actually confirmed.",
  },
  {
    icon: Send,
    title: "Publish",
    description:
      "A human approves every item before it ships to the public site.",
  },
];

const PRINCIPLES = [
  {
    title: "Human sign-off",
    description:
      "Machines draft, editors decide. Nothing is published without an explicit approval.",
  },
  {
    title: "Citable by default",
    description:
      "Every claim tracks back to a source. Unverifiable assertions never ship.",
  },
  {
    title: "Transparent pipeline",
    description:
      "The full path from RSS item to published article is visible in the operator console.",
  },
];

export default function HomePage() {
  return (
    <div className="flex min-h-svh flex-col">
      <SiteHeader />
      <main className="flex-1">
        <section className="border-b">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-20 sm:px-6 sm:py-24">
            <div className="max-w-3xl space-y-6">
              <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                AI Newsroom
              </p>
              <h1 className="text-balance text-4xl font-semibold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
                Evidence-backed journalism,
                <br className="hidden sm:block" /> assembled by machines,
                signed off by people.
              </h1>
              <p className="max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
                AI Newsroom is a single-operator command center for a
                journalism pipeline: sources are ingested, claims are
                researched and verified, articles are drafted — and every issue
                that reaches the public has passed human review.
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link
                  href="/dashboard"
                  className={cn(
                    buttonVariants({ variant: "default", size: "lg" }),
                    "gap-2",
                  )}
                >
                  Open the operator console
                  <ArrowRight className="size-4" />
                </Link>
                <Link
                  href="/latest"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "lg" }),
                  )}
                >
                  Read the latest
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="border-b">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <div className="mb-10 flex items-end justify-between gap-4">
              <div className="space-y-1">
                <h2 className="text-2xl font-semibold tracking-tight">
                  How it works
                </h2>
                <p className="text-sm text-muted-foreground">
                  Five stages, one pipeline, zero unverified claims.
                </p>
              </div>
              <Newspaper className="hidden size-8 text-muted-foreground/40 sm:block" />
            </div>
            <ol className="grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 lg:grid-cols-5">
              {PIPELINE_STEPS.map((step, index) => (
                <li
                  key={step.title}
                  className="flex flex-col gap-3 bg-card p-5"
                >
                  <div className="flex items-center justify-between">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-foreground">
                      <step.icon className="size-4" />
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      0{index + 1}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold">{step.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-b">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold tracking-tight">
                Editorial principles
              </h2>
              <p className="text-sm text-muted-foreground">
                The rules that keep automation honest.
              </p>
            </div>
            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {PRINCIPLES.map((principle) => (
                <div
                  key={principle.title}
                  className="rounded-xl border bg-card p-5"
                >
                  <h3 className="text-sm font-semibold">
                    {principle.title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {principle.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section>
          <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6">
            <h2 className="max-w-xl text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
              Ready to run the newsroom?
            </h2>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className={cn(buttonVariants({ variant: "default" }), "gap-2")}
              >
                Go to dashboard
                <ArrowRight className="size-4" />
              </Link>
              <Link
                href="/about"
                className={cn(buttonVariants({ variant: "ghost" }))}
              >
                Learn about the project
              </Link>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}