import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type SectionShellProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  children?: React.ReactNode;
};

export function SectionShell({
  icon,
  title,
  description,
  emptyTitle,
  emptyDescription,
  children,
}: SectionShellProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={icon}
          title={emptyTitle}
          description={emptyDescription}
        >
          {children}
        </EmptyState>
      </CardContent>
    </Card>
  );
}