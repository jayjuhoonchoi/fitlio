"use client";

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

import { cohortData, revenueTrend } from "@/lib/mock-data";

export function AnalyticsCharts(): JSX.Element {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-3 text-sm font-medium">MRR · Retention · Occupancy</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={revenueTrend}>
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
      </div>

      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <p className="mb-3 text-sm font-medium">Cohort Analysis (Zen-style)</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cohortData}>
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
