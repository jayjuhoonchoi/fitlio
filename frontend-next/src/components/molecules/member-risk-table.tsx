import { Badge } from "@/components/atoms/badge";
import { members } from "@/lib/mock-data";

export function MemberRiskTable(): JSX.Element {
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
          {members.map((member) => {
            const atRisk = member.attendanceRate <= 50;
            return (
              <tr key={member.id} className="border-t border-border/80">
                <td className="px-3 py-2 font-medium">{member.memberNo}</td>
                <td className="px-3 py-2">{member.name}</td>
                <td className="px-3 py-2 text-muted">{member.email}</td>
                <td className="px-3 py-2 uppercase text-silver">{member.level}</td>
                <td className="px-3 py-2">
                  <Badge tone={member.active ? "accent" : "neutral"}>
                    {member.active ? "ACTIVE" : "PAUSED"}
                  </Badge>
                </td>
                <td className="px-3 py-2">{member.attendanceRate}%</td>
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
