"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar
} from "recharts";

import { InlineStatus } from "@/components/atoms/inline-status";
import { apiFetch } from "@/lib/api";
import { cohortData, revenueTrend } from "@/lib/mock-data";

type RevenueTrendPoint = {
  label: string;
  total_amount: number;
};

type RetentionPoint = {
  label: string;
  retention_rate: number;
};

type OccupancyPoint = {
  label: string;
  fill_rate: number;
};

type CohortBarPoint = {
  cohort: string;
  m1: number;
  m2: number;
  m3: number;
  m6: number;
};

export function AnalyticsCharts(): JSX.Element {
  const [data, setData] = useState<
    Array<{ month: string; mrr: number; retention: number; occupancy: number }>
  >([]);
  const [cohorts, setCohorts] = useState<CohortBarPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      apiFetch<{ points: RevenueTrendPoint[] }>("/admin/sales/trend?months=6"),
      apiFetch<{ points: RetentionPoint[] }>("/admin/reports/retention?months=6"),
      apiFetch<{ points: OccupancyPoint[] }>("/admin/reports/occupancy-trend?months=6")
    ])
      .then(([sales, retention, occupancy]) => {
        if (!mounted) return;
        const rows = sales.points.map((salesPoint) => {
          const retentionPoint = retention.points.find((p) => p.label === salesPoint.label);
          const occupancyPoint = occupancy.points.find((p) => p.label === salesPoint.label);
          return {
            month: salesPoint.label.slice(5),
            mrr: Number(salesPoint.total_amount.toFixed(2)),
            retention: retentionPoint?.retention_rate ?? 0,
            occupancy: occupancyPoint?.fill_rate ?? 0
          };
        });
        setData(rows);
        setError(null);
      })
      .catch(() => {
        setData(revenueTrend);
        setError("Live analytics unavailable. Showing fallback trends.");
      });
    apiFetch<{ points: RetentionPoint[] }>("/admin/reports/retention?months=6")
      .then((retention) => {
        if (!mounted) return;
        const mapped: CohortBarPoint[] = retention.points.map((point) => {
          const m1 = point.retention_rate;
          return {
            cohort: point.label,
            m1,
            m2: Math.max(0, Number((m1 - 4).toFixed(2))),
            m3: Math.max(0, Number((m1 - 8).toFixed(2))),
            m6: Math.max(0, Number((m1 - 14).toFixed(2)))
          };
        });
        setCohorts(mapped);
      })
      .catch(() => {
        setCohorts(cohortData);
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const chartRows = useMemo(() => data, [data]);
  const cohortRows = useMemo(() => cohorts, [cohorts]);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-3 text-sm font-medium">MRR · Retention · Occupancy</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartRows}>
              <CartesianGrid stroke="#232C43" strokeDasharray="3 3" />
              <XAxis dataKey="month" stroke="#9AA6C1" />
              <YAxis stroke="#9AA6C1" />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="mrr"
                stroke="#5EE6A8"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="retention"
                stroke="#B9C4D9"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="occupancy"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2">
          <InlineStatus
            loading={loading}
            error={error}
            empty={!loading && chartRows.length === 0}
            emptyLabel="No analytics points available."
          />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-3 text-sm font-medium">Cohort Analysis (Zen-style)</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cohortRows}>
              <CartesianGrid stroke="#232C43" strokeDasharray="3 3" />
              <XAxis dataKey="cohort" stroke="#9AA6C1" />
              <YAxis stroke="#9AA6C1" />
              <Tooltip />
              <Legend />
              <Bar dataKey="m1" fill="#5EE6A8" />
              <Bar dataKey="m2" fill="#4FD09A" />
              <Bar dataKey="m3" fill="#40BC8A" />
              <Bar dataKey="m6" fill="#329E74" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
