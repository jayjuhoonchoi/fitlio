"use client";

import { useRouter } from "next/navigation";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { useFitlioSession } from "@/hooks/use-fitlio-session";
import { clearSession } from "@/lib/session";

export function UserMenu(): JSX.Element | null {
  const session = useFitlioSession();
  const router = useRouter();

  if (!session) {
    return null;
  }

  function handleLogout(): void {
    clearSession();
    router.replace("/");
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-panelElevated px-3 py-2 text-sm">
      <Badge tone={session.role === "admin" ? "accent" : "neutral"}>
        {session.role.toUpperCase()}
      </Badge>
      <span className="text-silver">
        {session.fullName || `Member #${session.memberId}`}
      </span>
      <ActionButton tone="ghost" className="ml-auto" onClick={handleLogout}>
        Sign out
      </ActionButton>
    </div>
  );
}
