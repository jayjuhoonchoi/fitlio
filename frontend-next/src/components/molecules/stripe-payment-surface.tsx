"use client";

import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";

const stripePromise = loadStripe("pk_test_fitlio_placeholder_public_key");

export function StripePaymentSurface(): JSX.Element {
  return (
    <Elements stripe={stripePromise}>
      <div className="rounded-xl border border-border bg-panelElevated p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium">Global Payments (Stripe Elements)</p>
          <Badge tone="accent">Subscription + Dunning</Badge>
        </div>
        <div className="rounded-lg border border-border bg-panel p-3">
          <p className="text-xs text-muted">
            Stripe Elements placeholder surface. Next step wires CardElement / PaymentElement
            with server-side subscription intent + dunning automation.
          </p>
        </div>
        <div className="mt-3 flex gap-2">
          <ActionButton>Create Subscription</ActionButton>
          <ActionButton tone="ghost">Retry Failed Invoice</ActionButton>
        </div>
      </div>
    </Elements>
  );
}
