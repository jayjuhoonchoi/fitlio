"use client";

import { RequireSession } from "@/components/guards/require-session";
import { DashboardLayout } from "@/components/organisms/dashboard-layout";

export default function AdminAppPage(): JSX.Element {
  return (
    <RequireSession role="admin">
      <DashboardLayout mode="admin" />
    </RequireSession>
  );
}
