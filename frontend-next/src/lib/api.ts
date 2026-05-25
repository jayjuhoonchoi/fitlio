"use client";

import { getAuthToken } from "@/lib/session";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const DEFAULT_TIMEOUT_MS = 8000;

export class ApiFetchError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "ApiFetchError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
      signal: controller.signal
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail =
        typeof payload?.detail === "string" ? payload.detail : "Request failed";
      throw new ApiFetchError(detail, response.status);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiFetchError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiFetchError(
        "API unreachable (start Docker: bash ~/fitlio/scripts/dev_local.sh)"
      );
    }
    throw new ApiFetchError(
      error instanceof Error ? error.message : "Network request failed"
    );
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function pingApiHealth(timeoutMs = 4000): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${baseUrl}/health`, {
      signal: controller.signal
    });
    if (!response.ok) {
      return false;
    }
    const payload = await response.json().catch(() => ({}));
    return payload?.status === "healthy";
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}
