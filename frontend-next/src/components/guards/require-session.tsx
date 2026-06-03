"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { loginPathForRole } from "@/lib/auth-routes";
import { readSession } from "@/lib/session";

type RequireSessionProps = {
  role: "member" | "admin";
  children: ReactNode;
};

export function RequireSession({ role, children }: RequireSessionProps): JSX.Element {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const session = readSession();
    if (!session) {
      router.replace(loginPathForRole(role));
      return;
    }
    if (role === "admin" && session.role !== "admin") {
      router.replace("/app/member");
      return;
    }
    if (role === "member" && session.role === "admin") {
      router.replace("/app/admin");
      return;
    }
    setReady(true);
  }, [role, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg text-sm text-muted">
        Loading…
      </div>
    );
  }

  return <>{children}</>;
}
