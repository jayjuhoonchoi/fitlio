"use client";

import { useState } from "react";

import { ActionButton } from "@/components/atoms/action-button";
import { whiteLabelSiteDefault } from "@/lib/mock-data";
import type { WhiteLabelSiteConfig } from "@/types/domain";

export function WhiteLabelCMSSurface(): JSX.Element {
  const [config, setConfig] = useState<WhiteLabelSiteConfig>(whiteLabelSiteDefault);

  return (
    <div className="rounded-xl border border-border bg-panelElevated p-4">
      <p className="mb-3 text-sm font-medium">White-label CMS (Subdomain + Editor)</p>
      <div className="grid gap-3">
        <label className="grid gap-1 text-xs text-muted">
          Center Name
          <input
            className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text"
            value={config.centerName}
            onChange={(event) =>
              setConfig((prev) => ({ ...prev, centerName: event.target.value }))
            }
          />
        </label>
        <label className="grid gap-1 text-xs text-muted">
          Subdomain
          <input
            className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text"
            value={config.subdomain}
            onChange={(event) =>
              setConfig((prev) => ({ ...prev, subdomain: event.target.value }))
            }
          />
        </label>
        <label className="grid gap-1 text-xs text-muted">
          Headline
          <input
            className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text"
            value={config.headline}
            onChange={(event) =>
              setConfig((prev) => ({ ...prev, headline: event.target.value }))
            }
          />
        </label>
        <label className="grid gap-1 text-xs text-muted">
          Body (Notion-style editor scaffold)
          <textarea
            className="min-h-28 rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text"
            value={config.body}
            onChange={(event) =>
              setConfig((prev) => ({ ...prev, body: event.target.value }))
            }
          />
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <ActionButton>Save Landing Content</ActionButton>
        <ActionButton tone="ghost">Preview Page</ActionButton>
      </div>
    </div>
  );
}
