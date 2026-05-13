import type { ReactNode } from "react";

type SectionShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function SectionShell({
  title,
  subtitle,
  children
}: SectionShellProps): JSX.Element {
  return (
    <section className="rounded-xl2 border border-border bg-panel p-5 shadow-soft">
      <header className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="text-sm text-muted">{subtitle}</p>
      </header>
      {children}
    </section>
  );
}
