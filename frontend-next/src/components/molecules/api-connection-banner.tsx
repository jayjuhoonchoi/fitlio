"use client";

import { useEffect, useState } from "react";

import { pingApiHealth } from "@/lib/api";

export function ApiConnectionBanner(): JSX.Element | null {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    pingApiHealth()
      .then((ok) => {
        if (mounted) {
          setOnline(ok);
        }
      })
      .catch(() => {
        if (mounted) {
          setOnline(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (online !== false) {
    return null;
  }

  return (
    <div className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
      API is offline. Start Docker Desktop, then run{" "}
      <code className="rounded bg-panel px-1 py-0.5 text-[11px] text-text">
        bash ~/fitlio/scripts/dev_local.sh
      </code>{" "}
      and refresh this page.
    </div>
  );
}
