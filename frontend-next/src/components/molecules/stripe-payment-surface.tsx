"use client";

import { useEffect, useState } from "react";
import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { InlineStatus } from "@/components/atoms/inline-status";
import { apiFetch } from "@/lib/api";

const stripePromise = loadStripe("pk_test_fitlio_placeholder_public_key");

export function StripePaymentSurface(): JSX.Element {
  const [memberId, setMemberId] = useState<string>("");
  const [history, setHistory] = useState<
    Array<{ id: number; amount: number; currency: string; status: string; created_at: string }>
  >([]);
  const [flash, setFlash] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const id = window.localStorage.getItem("member_id") ?? "";
    setMemberId(id);
    if (!id) {
      setLoading(false);
      return;
    }
    apiFetch<Array<{ id: number; amount: number; currency: string; status: string; created_at: string }>>(
      `/payments/history/${id}`
    )
      .then((rows) => {
        setHistory(rows);
        setError(null);
      })
      .catch(() => {
        setHistory([]);
        setError("Payment history unavailable.");
      })
      .finally(() => setLoading(false));
  }, []);

  async function purchase(plan: "monthly" | "yearly"): Promise<void> {
    if (!memberId) {
      setFlash("Login required for subscription.");
      return;
    }
    try {
      setLoading(true);
      await apiFetch(`/payments/membership?member_id=${memberId}`, {
        method: "POST",
        body: JSON.stringify({ plan })
      });
      setFlash(`Subscription created: ${plan}`);
      const rows = await apiFetch<
        Array<{ id: number; amount: number; currency: string; status: string; created_at: string }>
      >(`/payments/history/${memberId}`);
      setHistory(rows);
      setError(null);
    } catch (error) {
      setFlash(error instanceof Error ? error.message : "Payment failed");
      setError("Unable to refresh payment history.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Elements stripe={stripePromise}>
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium">Global Payments (Stripe Elements)</p>
          <Badge tone="accent">Subscription + Dunning</Badge>
        </div>
        <div className="rounded-lg border border-border bg-panel p-3">
          <p className="text-xs text-muted">
            Stripe Elements shell is live with membership purchase API and payment history.
            PaymentElement wiring is next for production cards and invoice retries.
          </p>
        </div>
        <div className="mt-3 flex gap-2">
          <ActionButton onClick={() => purchase("monthly")}>Start Monthly Plan</ActionButton>
          <ActionButton tone="ghost" onClick={() => purchase("yearly")}>
            Start Yearly Plan
          </ActionButton>
        </div>
        {flash ? <p className="mt-3 text-xs text-silver">{flash}</p> : null}
        <div className="mt-3 max-h-40 overflow-auto rounded-lg border border-border bg-panel p-3">
          <p className="mb-2 text-xs uppercase tracking-[0.15em] text-muted">Payment History</p>
          <ul className="space-y-1 text-xs text-silver">
            {history.map((row) => (
              <li key={row.id}>
                #{row.id} · {row.amount} {row.currency.toUpperCase()} · {row.status} ·{" "}
                {new Date(row.created_at).toLocaleString()}
              </li>
            ))}
            {history.length === 0 ? <li>No payments yet.</li> : null}
          </ul>
          <div className="mt-2">
            <InlineStatus
              loading={loading}
              error={error}
              empty={!loading && history.length === 0}
              emptyLabel="No successful payments yet."
            />
          </div>
        </div>
      </div>
    </Elements>
  );
}
