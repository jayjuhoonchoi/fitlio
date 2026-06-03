import type { FitlioSession } from "@/lib/session";

export function appPathForRole(role: string): string {
  return role === "admin" ? "/app/admin" : "/app/member";
}

export function loginPathForRole(role: "member" | "admin"): string {
  return role === "admin" ? "/admin-login" : "/login";
}

export function resolvePostLoginPath(session: FitlioSession, intended: "member" | "admin"): string {
  if (intended === "admin" && session.role !== "admin") {
    return loginPathForRole("admin");
  }
  if (intended === "member" && session.role === "admin") {
    return appPathForRole("admin");
  }
  return appPathForRole(session.role);
}
