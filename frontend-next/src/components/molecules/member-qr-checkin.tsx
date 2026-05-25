"use client";

import { useCallback, useEffect, useState } from "react";
import QRCode from "qrcode";

import { ActionButton } from "@/components/atoms/action-button";
import { InlineStatus } from "@/components/atoms/inline-status";
import { apiFetch } from "@/lib/api";
import { readSession, SESSION_CHANGED_EVENT } from "@/lib/session";

type CheckinQrPayload = {
  token: string;
  expires_at: string;
  expires_in_seconds: number;
};

export function MemberQrCheckin(): JSX.Element {
  const [nearestClass, setNearestClass] = useState<{ id: number; name: string } | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string>("");
  const [qrExpiresIn, setQrExpiresIn] = useState<number>(0);
  const [qrLoading, setQrLoading] = useState<boolean>(false);
  const [qrError, setQrError] = useState<string | null>(null);

  const refreshMemberQr = useCallback(async (): Promise<void> => {
    const session = readSession();
    if (!session) {
      setQrDataUrl("");
      setQrError("Sign in as a member to load your front-desk QR.");
      return;
    }
    if (session.role !== "member") {
      setQrDataUrl("");
      setQrError("Member account required (not admin).");
      return;
    }

    setQrLoading(true);
    setQrError(null);
    try {
      const payload = await apiFetch<CheckinQrPayload>("/member/checkin-qr");
      const dataUrl = await QRCode.toDataURL(payload.token, {
        margin: 1,
        width: 240,
        color: { dark: "#5EE6A8", light: "#0B1020" }
      });
      setQrDataUrl(dataUrl);
      setQrExpiresIn(payload.expires_in_seconds);
    } catch (error) {
      setQrDataUrl("");
      setQrError(error instanceof Error ? error.message : "Could not load QR");
    } finally {
      setQrLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMemberQr();
    apiFetch<{ id: number; name: string }>("/classes/nearest")
      .then((row) => setNearestClass({ id: row.id, name: row.name }))
      .catch(() => setNearestClass(null));

    const onSession = (): void => {
      void refreshMemberQr();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSession);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onSession);
  }, [refreshMemberQr]);

  useEffect(() => {
    if (qrExpiresIn <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setQrExpiresIn((prev) => {
        if (prev <= 1) {
          void refreshMemberQr();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [qrExpiresIn, refreshMemberQr]);

  return (
    <div className="rounded-xl border border-border bg-panelElevated p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.2em] text-silver">Your check-in QR</p>
        <ActionButton tone="ghost" onClick={() => void refreshMemberQr()} disabled={qrLoading}>
          Refresh
        </ActionButton>
      </div>
      <div className="mx-auto flex aspect-square max-w-[280px] items-center justify-center overflow-hidden rounded-2xl border border-accent/35 bg-accent/10 p-2">
        {qrDataUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={qrDataUrl} alt="Member check-in QR" className="h-full w-full object-contain" />
        ) : (
          <p className="px-4 text-center text-xs text-muted">
            {qrLoading ? "Loading QR…" : "Member sign-in unlocks your QR for the tablet scanner."}
          </p>
        )}
      </div>
      <p className="mt-2 text-xs text-muted">
        {nearestClass ? `Nearest class: ${nearestClass.name}` : "No upcoming class"}
      </p>
      {qrExpiresIn > 0 ? (
        <p className="mt-1 text-xs text-silver">Auto-refresh in {qrExpiresIn}s</p>
      ) : null}
      <div className="mt-2">
        <InlineStatus loading={qrLoading} error={qrError} empty={false} />
      </div>
    </div>
  );
}
