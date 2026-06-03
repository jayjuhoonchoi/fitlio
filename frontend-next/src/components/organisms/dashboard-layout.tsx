"use client";

import { useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { SectionErrorBoundary } from "@/components/errors/section-error-boundary";
import { StatCard } from "@/components/atoms/stat-card";
import { AdminAttendanceSurface } from "@/components/molecules/admin-attendance-surface";
import { AnalyticsCharts } from "@/components/molecules/analytics-charts";
import { ApiConnectionBanner } from "@/components/molecules/api-connection-banner";
import { LeftRail } from "@/components/molecules/left-rail";
import { MemberManagementSurface } from "@/components/molecules/member-management-surface";
import { MemberQrCheckin } from "@/components/molecules/member-qr-checkin";
import { MemberRiskTable } from "@/components/molecules/member-risk-table";
import { QuickReserveModal } from "@/components/molecules/quick-reserve-modal";
import { SectionShell } from "@/components/molecules/section-shell";
import { UserMenu } from "@/components/molecules/user-menu";
import { centerConfig } from "@/lib/center";
import { StripePaymentSurface } from "@/components/molecules/stripe-payment-surface";
import { WeeklyReportEmailPreview } from "@/components/molecules/weekly-report-email-preview";
import { WhiteLabelCMSSurface } from "@/components/molecules/whitelabel-cms-surface";
import { useFitlioSession } from "@/hooks/use-fitlio-session";
import type { DashboardCard, NavItem } from "@/types/layout";

const adminCards: DashboardCard[] = [
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

const memberCards: DashboardCard[] = [
  {
    key: "streak",
    title: "Check-in Streak",
    value: "4 days",
    helper: "Keep the rhythm going",
    trend: "up"
  },
  {
    key: "bookings",
    title: "Upcoming",
    value: "2 classes",
    helper: "Quick-reserve in two taps",
    trend: "neutral"
  },
  {
    key: "membership",
    title: "Membership",
    value: "Active",
    helper: "Renewal in 18 days",
    trend: "up"
  },
  {
    key: "visits",
    title: "Visits",
    value: "6 / 8",
    helper: "Monthly allowance",
    trend: "neutral"
  }
];

type DashboardLayoutProps = {
  mode: "member" | "admin";
};

export function DashboardLayout({ mode }: DashboardLayoutProps): JSX.Element {
  const session = useFitlioSession();
  const isAdmin = mode === "admin";
  const isMember = mode === "member";
  const role = mode;

  const [quickReserveOpen, setQuickReserveOpen] = useState<boolean>(false);
  const [activeNav, setActiveNav] = useState<NavItem["key"]>("dashboard");

  function scrollToSection(sectionId: string, key: NavItem["key"]): void {
    setActiveNav(key);
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const headline = isAdmin ? "Admin Console" : "Member App";
  const subtitle = isAdmin
    ? `${centerConfig.name} — operations, roster, and retention.`
    : `${centerConfig.name} — book classes, check in, and manage membership.`;

  return (
    <div className="flex min-h-screen bg-bg">
      <LeftRail activeKey={activeNav} role={role} onNavigate={scrollToSection} />
      <main className="flex-1 p-6">
        <header id="section-dashboard" className="mb-6 scroll-mt-6 space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-silver">
              {isAdmin ? "Administration" : "Member Experience"}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">{headline}</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted">{subtitle}</p>
          </div>
          <ApiConnectionBanner />
          <UserMenu />
        </header>

        <QuickReserveModal
          open={quickReserveOpen}
          onClose={() => setQuickReserveOpen(false)}
        />

        <SectionErrorBoundary title="KPI Surface">
          <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {(isAdmin ? adminCards : memberCards).map((card) => (
              <StatCard key={card.key} card={card} />
            ))}
          </section>
        </SectionErrorBoundary>

        {isMember ? (
          <section className="grid gap-4 xl:grid-cols-2">
            <SectionErrorBoundary title="Quick Reserve Surface">
              <div id="section-booking" className="scroll-mt-6">
                <SectionShell
                  title="Quick Reserve"
                  subtitle="Member booking with waitlist-ready UX"
                >
                  <p className="mb-3 text-sm text-muted">
                    Reserve in two taps. Full classes route you into the waitlist flow.
                  </p>
                  <ActionButton onClick={() => setQuickReserveOpen(true)}>
                    Open Quick Reserve
                  </ActionButton>
                </SectionShell>
              </div>
            </SectionErrorBoundary>

            <SectionErrorBoundary title="Member QR Check-in">
              <div id="section-checkin" className="scroll-mt-6">
                <SectionShell
                  title="Front Desk QR"
                  subtitle="Show this at the tablet kiosk scanner"
                >
                  <MemberQrCheckin />
                </SectionShell>
              </div>
            </SectionErrorBoundary>
          </section>
        ) : null}

        {isAdmin ? (
          <>
            <section className="mt-4">
              <SectionErrorBoundary title="Admin Attendance">
                <div id="section-checkin" className="scroll-mt-6">
                  <SectionShell
                    title="Attendance & Tablet"
                    subtitle="Front desk kiosk + instructor roster mark-present"
                  >
                    <AdminAttendanceSurface />
                  </SectionShell>
                </div>
              </SectionErrorBoundary>
            </section>

            <section className="mt-4">
              <SectionErrorBoundary title="Reporting Surface">
                <div id="section-reports" className="scroll-mt-6">
                  <SectionShell
                    title="Studio Reports"
                    subtitle="MRR, cohort, utilization, and retention risk"
                  >
                    <AnalyticsCharts />
                    <div className="mt-4">
                      <MemberRiskTable />
                    </div>
                  </SectionShell>
                </div>
              </SectionErrorBoundary>
            </section>

            <section className="mt-4 grid gap-4 xl:grid-cols-2">
              <SectionErrorBoundary title="White-label Surface">
                <div id="section-settings" className="scroll-mt-6">
                  <SectionShell
                    title="White-label CMS"
                    subtitle="Subdomain-ready landing editor scaffold"
                  >
                    <WhiteLabelCMSSurface />
                  </SectionShell>
                </div>
              </SectionErrorBoundary>

              <SectionErrorBoundary title="Email Surface">
                <SectionShell
                  title="Automated Weekly Report"
                  subtitle="Monday operator digest HTML preview"
                >
                  <WeeklyReportEmailPreview />
                </SectionShell>
              </SectionErrorBoundary>
            </section>

            <section id="section-members" className="mt-4 scroll-mt-6">
              <SectionErrorBoundary title="Member Management Surface">
                <SectionShell
                  title="Member Management"
                  subtitle="Admin-only roster edits (number, level, active state)"
                >
                  <MemberManagementSurface />
                </SectionShell>
              </SectionErrorBoundary>
            </section>
          </>
        ) : null}

        {session && (
          <section id="section-payments" className="mt-4 scroll-mt-6">
            <SectionErrorBoundary title="Payments Surface">
              <SectionShell
                title={isAdmin ? "Billing Overview" : "My Membership & Payments"}
                subtitle={
                  isAdmin
                    ? "Payment history scaffold for operator review"
                    : "Purchase plan and view payment history"
                }
              >
                <StripePaymentSurface />
              </SectionShell>
            </SectionErrorBoundary>
          </section>
        )}
      </main>
    </div>
  );
}
