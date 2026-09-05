import type { LucideIcon } from "lucide-react";
import {
  Bot,
  Camera,
  FileText,
  LayoutDashboard,
  Newspaper,
  Rss,
  Send,
  Settings,
  ShieldCheck,
  Telescope,
} from "lucide-react";

export type DashboardNavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  group: "Overview" | "Pipeline" | "Distribution" | "Operations";
};

export const DASHBOARD_NAV: DashboardNavItem[] = [
  {
    title: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    group: "Overview",
  },
  {
    title: "Stories",
    href: "/dashboard/stories",
    icon: Newspaper,
    group: "Pipeline",
  },
  {
    title: "Research",
    href: "/dashboard/research",
    icon: Telescope,
    group: "Pipeline",
  },
  {
    title: "Verification",
    href: "/dashboard/verification",
    icon: ShieldCheck,
    group: "Pipeline",
  },
  {
    title: "Articles",
    href: "/dashboard/articles",
    icon: FileText,
    group: "Pipeline",
  },
  {
    title: "Instagram",
    href: "/dashboard/instagram",
    icon: Camera,
    group: "Distribution",
  },
  {
    title: "Publishing",
    href: "/dashboard/publishing",
    icon: Send,
    group: "Distribution",
  },
  {
    title: "Sources",
    href: "/dashboard/sources",
    icon: Rss,
    group: "Operations",
  },
  {
    title: "Agents",
    href: "/dashboard/agents",
    icon: Bot,
    group: "Operations",
  },
  {
    title: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    group: "Operations",
  },
];

export const DASHBOARD_GROUPS = [
  "Overview",
  "Pipeline",
  "Distribution",
  "Operations",
] as const;

export function resolveDashboardTitle(pathname: string): string {
  const item = DASHBOARD_NAV.find(
    (entry) =>
      pathname === entry.href || pathname.startsWith(`${entry.href}/`),
  );
  return item?.title ?? "Dashboard";
}