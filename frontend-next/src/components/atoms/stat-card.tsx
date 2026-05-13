import { cn } from "@/lib/cn";
import type { DashboardCard } from "@/types/layout";

type StatCardProps = {
  card: DashboardCard;
};

const trendColor: Record<DashboardCard["trend"], string> = {
  up: "text-accent",
  down: "text-danger",
  neutral: "text-silver"
};

export function StatCard({ card }: StatCardProps): JSX.Element {
  return (
    <article className="rounded-xl2 border border-border bg-panel p-4 shadow-soft">
      <p className="text-xs text-muted">{card.title}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{card.value}</p>
      <p className={cn("mt-2 text-xs", trendColor[card.trend])}>{card.helper}</p>
    </article>
  );
}
