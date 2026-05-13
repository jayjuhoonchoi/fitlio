import { cn } from "@/lib/cn";

type BadgeProps = {
  children: string;
  tone?: "neutral" | "accent" | "danger";
};

const toneClass: Record<NonNullable<BadgeProps["tone"]>, string> = {
  neutral: "border-border bg-panelElevated text-silver",
  accent: "border-accent/30 bg-accent/15 text-accent",
  danger: "border-danger/35 bg-danger/15 text-danger"
};

export function Badge({
  children,
  tone = "neutral"
}: BadgeProps): JSX.Element {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-1 text-[11px] font-medium",
        toneClass[tone]
      )}
    >
      {children}
    </span>
  );
}
