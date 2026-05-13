import { SectionErrorBoundary } from "@/components/errors/section-error-boundary";
import { StatCard } from "@/components/atoms/stat-card";
import { LeftRail } from "@/components/molecules/left-rail";
import { SectionShell } from "@/components/molecules/section-shell";
import type { DashboardCard } from "@/types/layout";

const topCards: DashboardCard[] = [
  {
    key: "mrr",
    title: "MRR",
    value: "$126,840",
    helper: "+11.2% vs last month",
    trend: "up"
  },
  {
    key: "retention",
    title: "Retention",
    value: "84.7%",
    helper: "+2.1pp cohort uplift",
    trend: "up"
  },
  {
    key: "occupancy",
    title: "Class Occupancy",
    value: "78%",
    helper: "Prime-time classes trending up",
    trend: "up"
  },
  {
    key: "risk",
    title: "Churn Risk",
    value: "31 members",
    helper: "Needs intervention this week",
    trend: "down"
  }
];

export function DashboardLayout(): JSX.Element {
  return (
    <div className="flex min-h-screen bg-bg">
      <LeftRail />
      <main className="flex-1 p-6">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.2em] text-silver">
            Operations Console
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Studio Intelligence
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Mindbody-grade workflows with premium Glofox aesthetics. Designed for
            zero-friction booking, one-tap attendance, and retention-first decisioning.
          </p>
        </header>

        <SectionErrorBoundary title="KPI Surface">
          <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {topCards.map((card) => (
              <StatCard key={card.key} card={card} />
            ))}
          </section>
        </SectionErrorBoundary>

        <section className="grid gap-4 xl:grid-cols-3">
          <SectionErrorBoundary title="Quick Reserve Surface">
            <SectionShell
              title="Quick Reserve Modal Surface"
              subtitle="Step 1 scaffold: two-tap reserve interaction zone"
            >
              <div className="rounded-xl border border-border bg-panelElevated p-4 text-sm text-muted">
                Quick-Reserve / Waitlist implementation comes in next phase.
              </div>
            </SectionShell>
          </SectionErrorBoundary>

          <SectionErrorBoundary title="Check-in Surface">
            <SectionShell
              title="Check-in Surface"
              subtitle="Large QR viewport and one-tap attendance zone"
            >
              <div className="rounded-xl border border-border bg-panelElevated p-4 text-sm text-muted">
                QR + attendance gamification implementation follows after approval.
              </div>
            </SectionShell>
          </SectionErrorBoundary>

          <SectionErrorBoundary title="Reporting Surface">
            <SectionShell
              title="Reporting Surface"
              subtitle="Cohort, MRR, occupancy and risk segmentation shell"
            >
              <div className="rounded-xl border border-border bg-panelElevated p-4 text-sm text-muted">
                Recharts and retention predictor wiring is phase 2+.
              </div>
            </SectionShell>
          </SectionErrorBoundary>
        </section>
      </main>
    </div>
  );
}
