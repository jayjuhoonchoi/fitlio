"use client";

import { useEffect, useState } from "react";

import { readSession, SESSION_CHANGED_EVENT, type FitlioSession } from "@/lib/session";

export function useFitlioSession(): FitlioSession | null {
  const [session, setSession] = useState<FitlioSession | null>(null);

  useEffect(() => {
    setSession(readSession());
    const sync = (): void => setSession(readSession());
    window.addEventListener(SESSION_CHANGED_EVENT, sync);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, sync);
  }, []);

  return session;
}
