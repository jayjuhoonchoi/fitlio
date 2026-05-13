export function WeeklyReportEmailPreview(): JSX.Element {
  return (
    <div className="rounded-xl border border-border bg-panelElevated p-4">
      <p className="mb-3 text-sm font-medium">Automated Monday Report (HTML Email)</p>
      <div className="rounded-lg border border-border bg-white p-4 text-[#1f2937]">
        <p style={{ fontSize: "12px", color: "#6b7280" }}>Monday Performance Digest</p>
        <h3 style={{ marginTop: "8px", fontSize: "20px", fontWeight: 700 }}>
          Fitlio Weekly Studio Snapshot
        </h3>
        <p style={{ marginTop: "8px", fontSize: "14px" }}>
          MRR: <strong>$126,840</strong> (+11.2%) · Retention: <strong>84.7%</strong> ·
          Class Occupancy: <strong>78%</strong>
        </p>
        <hr style={{ margin: "14px 0", borderColor: "#e5e7eb" }} />
        <p style={{ fontSize: "13px" }}>
          At-risk members (attendance ≤ 50%): <strong>31</strong>
        </p>
        <p style={{ fontSize: "13px", marginTop: "4px" }}>
          Suggested actions: auto-winback message + coach outreach.
        </p>
      </div>
    </div>
  );
}
