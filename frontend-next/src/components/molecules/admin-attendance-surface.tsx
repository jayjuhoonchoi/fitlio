"use client";

import { useEffect, useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { InlineStatus } from "@/components/atoms/inline-status";
import { apiFetch } from "@/lib/api";
import { members as fallbackMembers } from "@/lib/mock-data";
import { readSession, SESSION_CHANGED_EVENT } from "@/lib/session";

type RosterRow = {
  booking_id: number;
  member_id: number;
  full_name: string;
  phone_last4?: string | null;
  checked_in_today: boolean;
};

type RosterResponse = {
  class: { id: number; name: string };
  roster: RosterRow[];
};

const TABLET_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export function AdminAttendanceSurface(): JSX.Element {
  const [classId, setClassId] = useState<number | null>(null);
  const [className, setClassName] = useState<string>("");
  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [marked, setMarked] = useState<number[]>([]);
  const [flash, setFlash] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadAdminContext(): Promise<void> {
    const session = readSession();
    if (!session || session.role !== "admin") {
      setError("Admin sign-in required for roster attendance.");
      setRoster(
        fallbackMembers.map((member, index) => ({
          booking_id: index + 1,
          member_id: index + 1,
          full_name: member.name,
          phone_last4: member.memberNo.slice(-4),
          checked_in_today: false
        }))
      );
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const nearest = await apiFetch<{ id: number; name: string }>("/classes/nearest");
      setClassId(nearest.id);
      setClassName(nearest.name);
      const payload = await apiFetch<RosterResponse>(`/admin/classes/${nearest.id}/roster`);
      setRoster(payload.roster);
    } catch (loadError) {
      setClassId(null);
      setClassName("");
      setRoster(
        fallbackMembers.map((member, index) => ({
          booking_id: index + 1,
          member_id: index + 1,
          full_name: member.name,
          phone_last4: member.memberNo.slice(-4),
          checked_in_today: false
        }))
      );
      setError(loadError instanceof Error ? loadError.message : "Could not load roster");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAdminContext();
    const onSession = (): void => {
      void loadAdminContext();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSession);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onSession);
  }, []);

  async function markPresent(memberId: number, bookingId: number): Promise<void> {
    if (!classId || readSession()?.role !== "admin") {
      setFlash("Admin + live API required to mark attendance.");
      return;
    }
    try {
      const result = await apiFetch<{ message: string }>(
        `/admin/classes/${classId}/attendance/${memberId}`,
        { method: "POST" }
      );
      setMarked((prev) => (prev.includes(bookingId) ? prev : [...prev, bookingId]));
      setFlash(result.message);
    } catch (markError) {
      setFlash(markError instanceof Error ? markError.message : "Mark present failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-silver">Front desk tablet</p>
        <p className="mt-2 text-sm text-muted">
          PIN + QR kiosk for members scanning phone QR at reception.
        </p>
        <ActionButton
          className="mt-3"
          onClick={() => window.open(`${TABLET_BASE}/app/tablet/cbd-flagship`, "_blank")}
        >
          Open Tablet Kiosk
        </ActionButton>
      </div>

      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-silver">
          Class roster · mark present
        </p>
        <p className="mb-3 text-xs text-muted">
          {className ? `Class: ${className}` : "No upcoming class loaded"}
        </p>
        <div className="space-y-2">
          {roster.map((row) => {
            const done = marked.includes(row.booking_id) || row.checked_in_today;
            return (
              <div
                key={row.booking_id}
                className="flex items-center justify-between rounded-lg border border-border bg-panel px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{row.full_name}</p>
                  <p className="text-xs text-muted">
                    {row.phone_last4 ? `···${row.phone_last4}` : "—"}
                  </p>
                </div>
                <ActionButton
                  tone={done ? "ghost" : "primary"}
                  onClick={() => void markPresent(row.member_id, row.booking_id)}
                >
                  {done ? "Present" : "Mark present"}
                </ActionButton>
              </div>
            );
          })}
        </div>
        <div className="mt-3">
          <InlineStatus
            loading={loading}
            error={error}
            empty={!loading && roster.length === 0}
            emptyLabel="No confirmed bookings on roster."
          />
        </div>
        {flash ? <p className="mt-2 text-xs text-accent">{flash}</p> : null}
      </div>
    </div>
  );
}
