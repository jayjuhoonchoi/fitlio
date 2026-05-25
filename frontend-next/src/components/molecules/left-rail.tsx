"use client";

import {
  BarChart3,
  CalendarCheck2,
  CreditCard,
  LayoutDashboard,
  QrCode,
  Settings,
  Users
} from "lucide-react";

import { AppLogo } from "@/components/atoms/app-logo";
import { IconNavButton } from "@/components/atoms/icon-nav-button";
import type { NavItem } from "@/types/layout";

export const navItems: NavItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    sectionId: "section-dashboard",
    roles: ["guest", "member", "admin"]
  },
  {
    key: "booking",
    label: "Booking",
    icon: CalendarCheck2,
    sectionId: "section-booking",
    roles: ["member"]
  },
  {
    key: "checkin",
    label: "Check-in",
    icon: QrCode,
    sectionId: "section-checkin",
    roles: ["member", "admin"]
  },
  {
    key: "members",
    label: "Members",
    icon: Users,
    sectionId: "section-members",
    roles: ["admin"]
  },
  {
    key: "reports",
    label: "Reports",
    icon: BarChart3,
    sectionId: "section-reports",
    roles: ["admin"]
  },
  {
    key: "payments",
    label: "Payments",
    icon: CreditCard,
    sectionId: "section-payments",
    roles: ["member", "admin"]
  },
  {
    key: "settings",
    label: "Settings",
    icon: Settings,
    sectionId: "section-settings",
    roles: ["admin"]
  }
];

type LeftRailProps = {
  activeKey: NavItem["key"];
  role: "guest" | "member" | "admin";
  onNavigate: (sectionId: string, key: NavItem["key"]) => void;
};

export function LeftRail({ activeKey, role, onNavigate }: LeftRailProps): JSX.Element {
  const visible = navItems.filter((item) => item.roles.includes(role));

  return (
    <aside className="flex h-screen w-20 flex-col items-center gap-6 border-r border-border bg-panel px-3 py-5">
      <AppLogo />
      <div className="flex flex-1 flex-col gap-3">
        {visible.map((item) => (
          <IconNavButton
            key={item.key}
            item={item}
            active={item.key === activeKey}
            onNavigate={(sectionId) => onNavigate(sectionId, item.key)}
          />
        ))}
      </div>
    </aside>
  );
}
