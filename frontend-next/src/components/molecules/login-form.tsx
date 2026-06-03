"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { ActionButton } from "@/components/atoms/action-button";
import { apiFetch } from "@/lib/api";
import { resolvePostLoginPath } from "@/lib/auth-routes";
import { writeSession, type FitlioSession } from "@/lib/session";

type LoginResponse = {
  access_token: string;
  member_id: number;
  full_name: string;
  role: string;
};

type LoginFormProps = {
  mode: "member" | "admin";
  title: string;
  subtitle: string;
};

export function LoginForm({ mode, title, subtitle }: LoginFormProps): JSX.Element {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function performLogin(nextEmail: string, nextPassword: string): Promise<void> {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: nextEmail, password: nextPassword })
      });
      const session: FitlioSession = {
        token: result.access_token,
        memberId: String(result.member_id),
        fullName: result.full_name,
        role: result.role
      };
      if (mode === "admin" && session.role !== "admin") {
        setError("This account is not an administrator.");
        return;
      }
      writeSession(session);
      const target = resolvePostLoginPath(session, mode);
      if (target === "/admin-login" && mode === "admin") {
        setError("Administrator access required.");
        return;
      }
      router.replace(target);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await performLogin(email, password);
  }

  return (
    <div className="mx-auto w-full max-w-md rounded-xl2 border border-border bg-panel p-6 shadow-soft">
      <p className="text-xs uppercase tracking-[0.2em] text-silver">
        {mode === "admin" ? "Staff" : "Member"}
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-text">{title}</h1>
      <p className="mt-2 text-sm text-muted">{subtitle}</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-3">
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
          required
          className="w-full rounded-lg border border-border bg-panelElevated px-3 py-2.5 text-sm text-text outline-none focus:border-accent/60"
          autoComplete="username"
        />
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          required
          className="w-full rounded-lg border border-border bg-panelElevated px-3 py-2.5 text-sm text-text outline-none focus:border-accent/60"
          autoComplete="current-password"
        />
        <ActionButton type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </ActionButton>
      </form>
      {error ? <p className="mt-3 text-xs text-danger">{error}</p> : null}
    </div>
  );
}
