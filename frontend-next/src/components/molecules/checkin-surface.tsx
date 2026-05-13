"use client";

import { useMemo, useState } from "react";
import { QrCode } from "lucide-react";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { members } from "@/lib/mock-data";

export function CheckinSurface(): JSX.Element {
  const [checkedIds, setCheckedIds] = useState<string[]>([]);

  const streakMessage = useMemo(() => {
    if (checkedIds.length >= 3) return "Perfect Streak! +Retention XP";
    if (checkedIds.length > 0) return "Great consistency!";
    return "Scan QR or one-tap check attendance.";
  }, [checkedIds.length]);

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <div className="mb-4 flex items-center gap-2 text-silver">
          <QrCode className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.2em]">QR Check-in</p>
        </div>
        <div className="mx-auto flex aspect-square max-w-[280px] items-center justify-center rounded-2xl border border-accent/35 bg-accent/10">
          <div className="text-center">
            <QrCode className="mx-auto h-20 w-20 text-accent" />
            <p className="mt-3 text-xs text-silver">fitlio://checkin/cbd-flagship</p>
          </div>
        </div>
        <p className="mt-4 text-sm font-medium text-accent">{streakMessage}</p>
      </div>

      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-3 text-xs uppercase tracking-[0.2em] text-silver">
          One-tap Attendance
        </p>
        <div className="space-y-2">
          {members.map((member) => {
            const checked = checkedIds.includes(member.id);
            const atRisk = member.attendanceRate <= 50;
            return (
              <div
                key={member.id}
                className="flex items-center justify-between rounded-lg border border-border bg-panel px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{member.name}</p>
                  <p className="text-xs text-muted">{member.memberNo}</p>
                </div>
                <div className="flex items-center gap-2">
                  {atRisk ? <Badge tone="danger">At-Risk</Badge> : null}
                  <ActionButton
                    tone={checked ? "ghost" : "primary"}
                    onClick={() =>
                      setCheckedIds((prev) =>
                        prev.includes(member.id)
                          ? prev.filter((id) => id !== member.id)
                          : [...prev, member.id]
                      )
                    }
                  >
                    {checked ? "Checked" : "Check-in"}
                  </ActionButton>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
