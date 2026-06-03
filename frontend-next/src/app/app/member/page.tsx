"use client";

import { RequireSession } from "@/components/guards/require-session";
import { DashboardLayout } from "@/components/organisms/dashboard-layout";

export default function MemberAppPage(): JSX.Element {
  return (
    <RequireSession role="member">
      <DashboardLayout mode="member" />
    </RequireSession>
  );
}
