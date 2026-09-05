import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

type PublicPageShellProps = {
  eyebrow?: string;
  title: string;
  description: string;
  children?: React.ReactNode;
};

export function PublicPageShell({
  eyebrow,
  title,
  description,
  children,
}: PublicPageShellProps) {
  return (
    <div className="flex min-h-svh flex-col">
      <SiteHeader />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
          <div className="space-y-2">
            {eyebrow && (
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                {eyebrow}
              </p>
            )}
            <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            <p className="max-w-2xl text-pretty text-muted-foreground">
              {description}
            </p>
          </div>
          <div className="mt-10">{children}</div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}