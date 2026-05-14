from dataclasses import dataclass
from datetime import datetime
import uuid


SUPPORTED_METHODS = {"paypal", "naverpay", "kakaopay", "payco", "bank_transfer", "card"}


@dataclass
class PaymentIntent:
    provider: str
    external_ref: str
    status: str
    checkout_url: str


def create_payment_intent(method: str, amount_cents: int, currency: str = "aud") -> PaymentIntent:
    if method not in SUPPORTED_METHODS:
        raise ValueError("Unsupported payment method")
    # Adapter-ready structure. Real SDK calls can replace this later.
    rid = f"{method}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    return PaymentIntent(
        provider=method,
        external_ref=rid,
        status="pending",
        checkout_url=f"https://pay.fitlio.local/checkout/{rid}?amount={amount_cents}&currency={currency}",
    )
