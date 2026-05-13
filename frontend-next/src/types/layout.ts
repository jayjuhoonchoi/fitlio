import type { LucideIcon } from "lucide-react";

export type NavItem = {
  key:
    | "dashboard"
    | "booking"
    | "checkin"
    | "members"
    | "reports"
    | "payments"
    | "settings";
  label: string;
  icon: LucideIcon;
  href: string;
};

export type DashboardCard = {
  key: string;
  title: string;
  value: string;
  helper: string;
  trend: "up" | "down" | "neutral";
};
