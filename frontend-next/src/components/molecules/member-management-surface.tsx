"use client";

import { useCallback, useEffect, useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { InlineStatus } from "@/components/atoms/inline-status";
import { apiFetch } from "@/lib/api";
import { members as fallbackMembers } from "@/lib/mock-data";
import { readSession, SESSION_CHANGED_EVENT } from "@/lib/session";
import type { MemberLevel } from "@/types/domain";

const levels: MemberLevel[] = ["starter", "core", "elite", "vip"];

type AdminMemberRow = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  member_no: string | null;
  member_level: MemberLevel;
  is_active: boolean;
  attendance_rate?: number | null;
};

export function MemberManagementSurface(): JSX.Element {
  const [rows, setRows] = useState<AdminMemberRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string>("");

  const loadRows = useCallback(async (): Promise<void> => {
    const session = readSession();
    if (!session || session.role !== "admin") {
      setRows(
        fallbackMembers.map((member) => ({
          id: Number(member.id.replace("m-", "")) || 0,
          full_name: member.name,
          email: member.email,
          phone: member.phone,
          member_no: member.memberNo,
          member_level: member.level,
          is_active: member.active,
          attendance_rate: member.attendanceRate
        }))
      );
      setError(
        session ? "Admin login required for live member edits." : "Sign in as admin to load live roster."
      );
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const live = await apiFetch<AdminMemberRow[]>("/admin/members");
      setRows(live);
      setError(null);
    } catch (loadError) {
      setRows(
        fallbackMembers.map((member) => ({
          id: Number(member.id.replace("m-", "")) || 0,
          full_name: member.name,
          email: member.email,
          phone: member.phone,
          member_no: member.memberNo,
          member_level: member.level,
          is_active: member.active,
          attendance_rate: member.attendanceRate
        }))
      );
      setError(loadError instanceof Error ? loadError.message : "Could not load members");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRows();
    const onSession = (): void => {
      void loadRows();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSession);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onSession);
  }, [loadRows]);

  function updateRow(id: number, patch: Partial<AdminMemberRow>): void {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  async function saveAll(): Promise<void> {
    const session = readSession();
    if (!session || session.role !== "admin") {
      setFlash("Admin sign-in required to save.");
      return;
    }
    setSaving(true);
    setFlash("");
    try {
      await Promise.all(
        rows.map((row) =>
          apiFetch(`/admin/members/${row.id}`, {
            method: "PUT",
            body: JSON.stringify({
              full_name: row.full_name,
              phone: row.phone,
              member_no: row.member_no,
              member_level: row.member_level,
              is_active: row.is_active
            })
          })
        )
      );
      setFlash("Member configuration saved.");
      setError(null);
    } catch (saveError) {
      setFlash(saveError instanceof Error ? saveError.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-xl border border-border">
        <table className="w-full text-sm">
          <thead className="bg-panelElevated text-muted">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Member No</th>
              <th className="px-3 py-2 text-left font-medium">Name</th>
              <th className="px-3 py-2 text-left font-medium">Email</th>
              <th className="px-3 py-2 text-left font-medium">Phone</th>
              <th className="px-3 py-2 text-left font-medium">Level</th>
              <th className="px-3 py-2 text-left font-medium">Active</th>
              <th className="px-3 py-2 text-left font-medium">Retention Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const rate = row.attendance_rate ?? 100;
              const atRisk = rate <= 50;
              return (
                <tr key={row.id} className="border-t border-border/80">
                  <td className="px-3 py-2">
                    <input
                      value={row.member_no ?? ""}
                      onChange={(event) =>
                        updateRow(row.id, { member_no: event.target.value || null })
                      }
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={row.full_name}
                      onChange={(event) =>
                        updateRow(row.id, { full_name: event.target.value })
                      }
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2 text-muted">{row.email}</td>
                  <td className="px-3 py-2">
                    <input
                      value={row.phone}
                      onChange={(event) => updateRow(row.id, { phone: event.target.value })}
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={row.member_level}
                      onChange={(event) =>
                        updateRow(row.id, {
                          member_level: event.target.value as MemberLevel
                        })
                      }
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    >
                      {levels.map((level) => (
                        <option key={level} value={level}>
                          {level.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={row.is_active}
                        onChange={(event) =>
                          updateRow(row.id, { is_active: event.target.checked })
                        }
                      />
                      <span className="text-xs">{row.is_active ? "Active" : "Paused"}</span>
                    </label>
                  </td>
                  <td className="px-3 py-2">
                    {atRisk ? (
                      <Badge tone="danger">At-Risk</Badge>
                    ) : (
                      <Badge tone="accent">Healthy</Badge>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <InlineStatus
        loading={loading}
        error={error}
        empty={!loading && rows.length === 0}
        emptyLabel="No members loaded."
      />
      {flash ? <p className="text-xs text-accent">{flash}</p> : null}

      <div className="flex justify-end">
        <ActionButton onClick={() => void saveAll()} disabled={saving || loading}>
          {saving ? "Saving…" : "Save Member Configuration"}
        </ActionButton>
      </div>
    </div>
  );
}
