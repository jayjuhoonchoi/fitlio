"use client";

import { motion } from "framer-motion";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  tone?: "primary" | "ghost" | "danger";
};

const toneClass: Record<NonNullable<ActionButtonProps["tone"]>, string> = {
  primary:
    "border-accent/40 bg-accent/15 text-accent hover:border-accent/70 hover:bg-accent/20",
  ghost: "border-border bg-panel text-silver hover:border-silver/50 hover:text-text",
  danger:
    "border-danger/50 bg-danger/10 text-danger hover:border-danger/70 hover:bg-danger/20"
};

export function ActionButton({
  children,
  className,
  tone = "primary",
  ...props
}: ActionButtonProps): JSX.Element {
  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      className={cn(
        "rounded-lg border px-3 py-2 text-xs font-medium transition",
        toneClass[tone],
        className
      )}
      {...props}
    >
      {children}
    </motion.button>
  );
}
