/** Single-center launch (Gwanghwamun). Override via env on web Deployment. */
export const centerConfig = {
  slug: process.env.NEXT_PUBLIC_CENTER_SLUG ?? "gwanghwamun",
  name: process.env.NEXT_PUBLIC_CENTER_NAME ?? "Fitlio Gwanghwamun",
  tagline:
    process.env.NEXT_PUBLIC_CENTER_TAGLINE ??
    "Boutique studio operations — booking, check-in, and membership in one place."
} as const;
