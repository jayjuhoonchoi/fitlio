"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AppLogo } from "@/components/atoms/app-logo";
import { ActionButton } from "@/components/atoms/action-button";
import { centerConfig } from "@/lib/center";
import { appPathForRole } from "@/lib/auth-routes";
import { readSession } from "@/lib/session";

export function PortalLanding(): JSX.Element {
  const router = useRouter();

  useEffect(() => {
    const session = readSession();
    if (session) {
      router.replace(appPathForRole(session.role));
    }
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6 py-12">
      <div className="w-full max-w-lg rounded-xl2 border border-border bg-panel p-8 shadow-soft">
        <div className="mb-6 flex justify-center">
          <AppLogo />
        </div>
        <p className="text-center text-xs uppercase tracking-[0.2em] text-silver">
          {centerConfig.slug}
        </p>
        <h1 className="mt-2 text-center text-3xl font-semibold tracking-tight text-text">
          {centerConfig.name}
        </h1>
        <p className="mx-auto mt-3 max-w-md text-center text-sm leading-relaxed text-muted">
          {centerConfig.tagline}
        </p>
        <p className="mt-4 text-center text-xs text-silver">
          Members and staff only — Gwanghwamun pilot launch.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <Link href="/login" className="block">
            <ActionButton className="w-full">Member sign in</ActionButton>
          </Link>
          <Link href="/admin-login" className="block">
            <ActionButton tone="ghost" className="w-full">
              Admin sign in
            </ActionButton>
          </Link>
        </div>
      </div>
    </div>
  );
}
