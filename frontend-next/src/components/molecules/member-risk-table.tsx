"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/atoms/badge";
import { apiFetch } from "@/lib/api";
import { members as fallbackMembers } from "@/lib/mock-data";

type RiskMember = {
  id: number;
  full_name: string;
  email: string;
  member_no?: string | null;
  member_level?: string;
  is_active: boolean;
  attendance_rate: number;
};

export function MemberRiskTable(): JSX.Element {
  const [rows, setRows] = useState<RiskMember[]>([]);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      apiFetch<
        Array<{
          id: number;
          full_name: string;
          email: string;
          member_no?: string | null;
          member_level?: string;
          is_active: boolean;
        }>
      >("/admin/members"),
      apiFetch<
        Array<{
          member_id: number;
          attendance_rate: number;
        }>
      >("/admin/reports/member-risk")
    ])
      .then(([members, risk]) => {
        if (!mounted) return;
        const byMember = new Map<number, number>();
        risk.forEach((row) => byMember.set(row.member_id, row.attendance_rate));
        setRows(
          members.map((member) => ({
            ...member,
            attendance_rate: byMember.get(member.id) ?? 0
          }))
        );
      })
      .catch(() => {
        setRows(
          fallbackMembers.map((member) => ({
            id: Number(member.id.replace("m-", "")) || 0,
            full_name: member.name,
            email: member.email,
            member_no: member.memberNo,
            member_level: member.level,
            is_active: member.active,
            attendance_rate: member.attendanceRate
          }))
        );
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="overflow-hidden rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead className="bg-panelElevated text-muted">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Member No</th>
            <th className="px-3 py-2 text-left font-medium">Name</th>
            <th className="px-3 py-2 text-left font-medium">Email</th>
            <th className="px-3 py-2 text-left font-medium">Level</th>
            <th className="px-3 py-2 text-left font-medium">Active</th>
            <th className="px-3 py-2 text-left font-medium">Attendance</th>
            <th className="px-3 py-2 text-left font-medium">Risk</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((member) => {
            const atRisk = member.attendance_rate <= 50;
            return (
              <tr key={member.id} className="border-t border-border/80">
                <td className="px-3 py-2 font-medium">{member.member_no ?? `M-${member.id}`}</td>
                <td className="px-3 py-2">{member.full_name}</td>
                <td className="px-3 py-2 text-muted">{member.email}</td>
                <td className="px-3 py-2 uppercase text-silver">
                  {member.member_level ?? "starter"}
                </td>
                <td className="px-3 py-2">
                  <Badge tone={member.is_active ? "accent" : "neutral"}>
                    {member.is_active ? "ACTIVE" : "PAUSED"}
                  </Badge>
                </td>
                <td className="px-3 py-2">{member.attendance_rate}%</td>
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
  );
}
