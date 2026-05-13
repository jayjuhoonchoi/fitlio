"use client";

import { useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { members as initialMembers } from "@/lib/mock-data";
import type { Member, MemberLevel } from "@/types/domain";

const levels: MemberLevel[] = ["starter", "core", "elite", "vip"];

export function MemberManagementSurface(): JSX.Element {
  const [rows, setRows] = useState<Member[]>(initialMembers);

  function updateRow(id: string, patch: Partial<Member>): void {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
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
              const atRisk = row.attendanceRate <= 50;
              return (
                <tr key={row.id} className="border-t border-border/80">
                  <td className="px-3 py-2">
                    <input
                      value={row.memberNo}
                      onChange={(event) =>
                        updateRow(row.id, { memberNo: event.target.value })
                      }
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={row.name}
                      onChange={(event) => updateRow(row.id, { name: event.target.value })}
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={row.email}
                      onChange={(event) => updateRow(row.id, { email: event.target.value })}
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      value={row.phone}
                      onChange={(event) => updateRow(row.id, { phone: event.target.value })}
                      className="w-full rounded-md border border-border bg-panel px-2 py-1 text-xs text-text"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={row.level}
                      onChange={(event) =>
                        updateRow(row.id, { level: event.target.value as MemberLevel })
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
                        checked={row.active}
                        onChange={(event) =>
                          updateRow(row.id, { active: event.target.checked })
                        }
                      />
                      <span className="text-xs">{row.active ? "Active" : "Paused"}</span>
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

      <div className="flex justify-end">
        <ActionButton>Save Member Configuration</ActionButton>
      </div>
    </div>
  );
}
