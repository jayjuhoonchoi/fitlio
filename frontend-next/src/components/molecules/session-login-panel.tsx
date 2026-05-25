"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { apiFetch } from "@/lib/api";
import {
  clearSession,
  readSession,
  writeSession,
  SESSION_CHANGED_EVENT,
  type FitlioSession
} from "@/lib/session";

type LoginResponse = {
  access_token: string;
  member_id: number;
  full_name: string;
  role: string;
};

const MEMBER_DEMO = {
  email: "jay.choi@fitlio.com",
  password: "fitlio1234!"
};

const ADMIN_DEMO = {
  email: "admin@fitlio.com",
  password: "AdminFitlio1!"
};

export function SessionLoginPanel(): JSX.Element {
  const [session, setSession] = useState<FitlioSession | null>(null);
  const [email, setEmail] = useState(MEMBER_DEMO.email);
  const [password, setPassword] = useState(MEMBER_DEMO.password);
  const [error, setError] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setSession(readSession());
    const sync = (): void => setSession(readSession());
    window.addEventListener(SESSION_CHANGED_EVENT, sync);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, sync);
  }, []);

  async function performLogin(nextEmail: string, nextPassword: string): Promise<void> {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: nextEmail, password: nextPassword })
      });
      const nextSession: FitlioSession = {
        token: result.access_token,
        memberId: String(result.member_id),
        fullName: result.full_name,
        role: result.role
      };
      writeSession(nextSession);
      setSession(nextSession);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await performLogin(email, password);
  }

  function handleLogout(): void {
    clearSession();
    setSession(null);
    setError("");
    setEmail(MEMBER_DEMO.email);
    setPassword(MEMBER_DEMO.password);
  }

  if (session) {
    const modeLabel = session.role === "admin" ? "Admin console" : "Member app";
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-panelElevated px-3 py-2 text-sm">
        <Badge tone={session.role === "admin" ? "accent" : "neutral"}>
          {session.role.toUpperCase()}
        </Badge>
        <span className="text-silver">
          {modeLabel} · {session.fullName || `Member #${session.memberId}`}
        </span>
        <ActionButton tone="ghost" className="ml-auto" onClick={handleLogout}>
          Sign out
        </ActionButton>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-panelElevated p-3">
      <p className="mb-2 text-xs uppercase tracking-[0.2em] text-silver">Choose mode</p>
      <div className="mb-3 flex flex-wrap gap-2">
        <ActionButton
          type="button"
          disabled={submitting}
          onClick={() => void performLogin(MEMBER_DEMO.email, MEMBER_DEMO.password)}
        >
          Sign in as Member
        </ActionButton>
        <ActionButton
          type="button"
          tone="ghost"
          disabled={submitting}
          onClick={() => void performLogin(ADMIN_DEMO.email, ADMIN_DEMO.password)}
        >
          Sign in as Admin
        </ActionButton>
      </div>
      <form onSubmit={handleLogin} className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
          className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text outline-none focus:border-accent/60"
          autoComplete="username"
        />
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text outline-none focus:border-accent/60"
          autoComplete="current-password"
        />
        <ActionButton type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </ActionButton>
      </form>
      {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
    </div>
  );
}
