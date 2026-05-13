"use client";

import { useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { SectionErrorBoundary } from "@/components/errors/section-error-boundary";
import { StatCard } from "@/components/atoms/stat-card";
import { AnalyticsCharts } from "@/components/molecules/analytics-charts";
import { CheckinSurface } from "@/components/molecules/checkin-surface";
import { LeftRail } from "@/components/molecules/left-rail";
import { MemberRiskTable } from "@/components/molecules/member-risk-table";
import { MemberManagementSurface } from "@/components/molecules/member-management-surface";
import { QuickReserveModal } from "@/components/molecules/quick-reserve-modal";
import { SectionShell } from "@/components/molecules/section-shell";
import { StripePaymentSurface } from "@/components/molecules/stripe-payment-surface";
import { WeeklyReportEmailPreview } from "@/components/molecules/weekly-report-email-preview";
import { WhiteLabelCMSSurface } from "@/components/molecules/whitelabel-cms-surface";
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
  const [quickReserveOpen, setQuickReserveOpen] = useState<boolean>(false);

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

        <QuickReserveModal
          open={quickReserveOpen}
          onClose={() => setQuickReserveOpen(false)}
        />

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
              subtitle="Zero-friction booking with waitlist-ready UX"
            >
              <p className="mb-3 text-sm text-muted">
                Reserve in two taps. Full classes route members into waitlist flow.
              </p>
              <ActionButton onClick={() => setQuickReserveOpen(true)}>
                Open Quick Reserve
              </ActionButton>
            </SectionShell>
          </SectionErrorBoundary>

          <SectionErrorBoundary title="Check-in Surface">
            <SectionShell
              title="Check-in Surface"
              subtitle="QR check-in + instructor one-tap attendance"
            >
              <CheckinSurface />
            </SectionShell>
          </SectionErrorBoundary>

          <SectionErrorBoundary title="Reporting Surface">
            <SectionShell
              title="Reporting Surface"
              subtitle="MRR, cohort, utilization, and retention risk"
            >
              <AnalyticsCharts />
              <div className="mt-4">
                <MemberRiskTable />
              </div>
            </SectionShell>
          </SectionErrorBoundary>
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-2">
          <SectionErrorBoundary title="Payments Surface">
            <SectionShell
              title="Stripe Global Billing"
              subtitle="Subscription + dunning management scaffold"
            >
              <StripePaymentSurface />
            </SectionShell>
          </SectionErrorBoundary>

          <SectionErrorBoundary title="White-label Surface">
            <SectionShell
              title="White-label CMS"
              subtitle="Subdomain-ready landing editor scaffold"
            >
              <WhiteLabelCMSSurface />
            </SectionShell>
          </SectionErrorBoundary>
        </section>

        <section className="mt-4">
          <SectionErrorBoundary title="Member Management Surface">
            <SectionShell
              title="Member Management Console"
              subtitle="Admin can set member number, contact, active state, and level"
            >
              <MemberManagementSurface />
            </SectionShell>
          </SectionErrorBoundary>
        </section>

        <section className="mt-4">
          <SectionErrorBoundary title="Email Surface">
            <SectionShell
              title="Automated Weekly Report"
              subtitle="Monday operator digest HTML preview"
            >
              <WeeklyReportEmailPreview />
            </SectionShell>
          </SectionErrorBoundary>
        </section>
      </main>
    </div>
  );
}
