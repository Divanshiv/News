import { Badge } from "@/components/ui/badge";

export type StoryStatus =
  | "DISCOVERED"
  | "RESEARCHING"
  | "VERIFICATION"
  | "DRAFT"
  | "REVIEW"
  | "APPROVED"
  | "PUBLISHED"
  | "REJECTED"
  | "MERGED";

type StatusStyle = {
  label: string;
  dot: string;
  badge: string;
};

const STATUS_STYLES: Record<StoryStatus, StatusStyle> = {
  DISCOVERED: {
    label: "Discovered",
    dot: "bg-blue-500",
    badge:
      "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:border-blue-400/30 dark:text-blue-400",
  },
  RESEARCHING: {
    label: "Researching",
    dot: "bg-amber-500",
    badge:
      "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:border-amber-400/30 dark:text-amber-400",
  },
  VERIFICATION: {
    label: "Verification",
    dot: "bg-purple-500",
    badge:
      "border-purple-500/30 bg-purple-500/10 text-purple-600 dark:border-purple-400/30 dark:text-purple-400",
  },
  DRAFT: {
    label: "Draft",
    dot: "bg-zinc-400",
    badge:
      "border-zinc-400/40 bg-zinc-500/10 text-zinc-500 dark:border-zinc-400/30 dark:text-zinc-400",
  },
  REVIEW: {
    label: "Review",
    dot: "bg-amber-500",
    badge:
      "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:border-amber-400/30 dark:text-amber-400",
  },
  APPROVED: {
    label: "Approved",
    dot: "bg-green-500",
    badge:
      "border-green-500/30 bg-green-500/10 text-green-600 dark:border-green-400/30 dark:text-green-400",
  },
  PUBLISHED: {
    label: "Published",
    dot: "bg-emerald-500",
    badge:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:border-emerald-400/30 dark:text-emerald-400",
  },
  REJECTED: {
    label: "Rejected",
    dot: "bg-red-500",
    badge:
      "border-red-500/30 bg-red-500/10 text-red-600 dark:border-red-400/30 dark:text-red-400",
  },
  MERGED: {
    label: "Merged",
    dot: "bg-slate-400",
    badge:
      "border-slate-400/40 bg-slate-500/10 text-slate-500 dark:border-slate-400/30 dark:text-slate-400",
  },
};

export function StatusBadge({ status }: { status: StoryStatus }) {
  const style = STATUS_STYLES[status];
  return (
    <Badge className={style.badge}>
      <span aria-hidden className={`size-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </Badge>
  );
}

export const STORY_STATUSES = Object.keys(STATUS_STYLES) as StoryStatus[];