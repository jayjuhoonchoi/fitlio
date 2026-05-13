"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { cn } from "@/lib/cn";
import type { NavItem } from "@/types/layout";

type IconNavButtonProps = {
  item: NavItem;
  active?: boolean;
};

export function IconNavButton({
  item,
  active = false
}: IconNavButtonProps): JSX.Element {
  const Icon = item.icon;
  return (
    <Link href={item.href} aria-label={item.label} title={item.label}>
      <motion.div
        whileHover={{ y: -2 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "group relative flex h-11 w-11 items-center justify-center rounded-xl border transition",
          active
            ? "border-accent/70 bg-accent/15 text-accent"
            : "border-border bg-panel text-muted hover:border-silver/45 hover:text-text"
        )}
      >
        <Icon className="h-4 w-4" />
      </motion.div>
    </Link>
  );
}
