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

const navItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "#" },
  { key: "booking", label: "Booking", icon: CalendarCheck2, href: "#" },
  { key: "checkin", label: "Check-in", icon: QrCode, href: "#" },
  { key: "members", label: "Members", icon: Users, href: "#" },
  { key: "reports", label: "Reports", icon: BarChart3, href: "#" },
  { key: "payments", label: "Payments", icon: CreditCard, href: "#" },
  { key: "settings", label: "Settings", icon: Settings, href: "#" }
];

export function LeftRail(): JSX.Element {
  return (
    <aside className="flex h-screen w-20 flex-col items-center gap-6 border-r border-border bg-panel px-3 py-5">
      <AppLogo />
      <div className="flex flex-1 flex-col gap-3">
        {navItems.map((item, idx) => (
          <IconNavButton
            key={item.key}
            item={item}
            active={idx === 0}
          />
        ))}
      </div>
    </aside>
  );
}
