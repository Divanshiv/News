import type { Metadata } from "next";
import { CheckCircle2, GitBranch, Scale } from "lucide-react";

import { PublicPageShell } from "@/components/public-page-shell";

export const metadata: Metadata = {
  title: "About",
  description:
    "Why AI Newsroom exists and how the evidence-backed pipeline works.",
};

const STAGES = [
  {
    title: "Ingestion",
    body: "RSS feeds and registered sources are pulled into the queue as raw story candidates. Nothing here is considered journalism yet — it is signal awaiting triage.",
  },
  {
    title: "Research",
    body: "For each story that survives triage, agents assemble background, related coverage, and corroborating references so a claim can be examined in context.",
  },
  {
    title: "Verification",
    body: "The core editorial gate. Statements are checked against sources. A claim with no verifiable evidence is flagged, shelved, or rejected.",
  },
  {
    title: "Writing",
    body: "Drafts are generated strictly from the verified research material and per-source citations. Speculation is not an output.",
  },
  {
    title: "Human approval",
    body: "Every article passes through an operator review. Nothing reaches the public site — or Instagram — without explicit sign-off.",
  },
  {
    title: "Publication",
    body: "Approved items are published, archived, and indexed so the public record stays searchable and accountable.",
  },
];

export default function AboutPage() {
  return (
    <PublicPageShell
      eyebrow="About the project"
      title="A newsroom built on verification"
      description="AI Newsroom is a single-operator pipeline that treats automation as an assistant and evidence as the boss."
    >
      <div className="space-y-12">
        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border p-5 lg:col-span-1">
            <Scale className="size-5 text-muted-foreground" />
            <h2 className="mt-3 text-sm font-semibold">Why it exists</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Automated journalism is fast, but speed without verification
              just scales misinformation. AI Newsroom exists to keep the
              human judgement in the loop while the machinery does the labour
              — intake, research, and drafting at volume.
            </p>
          </div>
          <div className="rounded-xl border p-5">
            <GitBranch className="size-5 text-muted-foreground" />
            <h2 className="mt-3 text-sm font-semibold">The pipeline</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Six connected stages move a story from raw feed to published
              article. The operator console surfaces the state of every item
              and every stage so nothing is a black box.
            </p>
          </div>
          <div className="rounded-xl border p-5">
            <CheckCircle2 className="size-5 text-muted-foreground" />
            <h2 className="mt-3 text-sm font-semibold">The standard</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Every published article is traceable back to the sources that
              informed it. If a claim cannot be verified, it does not ship.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold tracking-tight">
            Six stages, start to finish
          </h2>
          <ol className="mt-6 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 lg:grid-cols-3">
            {STAGES.map((stage, index) => (
              <li key={stage.title} className="flex flex-col gap-2 bg-card p-5">
                <span className="font-mono text-xs text-muted-foreground">
                  Stage {index + 1}
                </span>
                <h3 className="text-sm font-semibold">{stage.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {stage.body}
                </p>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </PublicPageShell>
  );
}