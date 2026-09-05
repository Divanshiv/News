"use client";

import { usePathname } from "next/navigation";
import { Newspaper } from "lucide-react";

import { DASHBOARD_GROUPS, DASHBOARD_NAV } from "@/components/dashboard/nav-config";
import { Badge } from "@/components/ui/badge";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-1 py-1">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-foreground text-background">
            <Newspaper className="size-4" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-sm font-semibold tracking-tight">
              AI Newsroom
            </span>
            <span className="truncate text-[0.65rem] uppercase tracking-widest text-muted-foreground">
              Operator Console
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {DASHBOARD_GROUPS.map((group) => {
          const items = DASHBOARD_NAV.filter((item) => item.group === group);
          if (items.length === 0) return null;
          return (
            <SidebarGroup key={group}>
              <SidebarGroupLabel>{group}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {items.map((item) => {
                    const isActive =
                      pathname === item.href ||
                      pathname.startsWith(`${item.href}/`);
                    return (
                      <SidebarMenuItem key={item.href}>
                        <SidebarMenuButton
                          isActive={isActive}
                          tooltip={item.title}
                          render={<a href={item.href} />}
                        >
                          <item.icon />
                          <span>{item.title}</span>
                          {isActive && (
                            <SidebarMenuBadge>
                              <span className="size-1 rounded-full bg-sidebar-primary" />
                            </SidebarMenuBadge>
                          )}
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          );
        })}
      </SidebarContent>

      <SidebarFooter>
        <div className="flex items-center gap-2 px-1 py-1">
          <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            v0.1.0
          </Badge>
          <span className="truncate text-xs text-muted-foreground">
            Evidence-backed pipeline
          </span>
        </div>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}