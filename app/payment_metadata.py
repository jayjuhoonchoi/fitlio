from __future__ import annotations


_METHOD_PROFILES: dict[str, dict] = {
    "card": {
        "provider": "card_gateway_sim",
        "provider_display": "Card",
        "fee_hint_bps": 290,
        "settlement_mode": "auto",
        "settlement_timing_hint": "t+2_business_days",
    },
    "paypal": {
        "provider": "paypal",
        "provider_display": "PayPal",
        "fee_hint_bps": 349,
        "settlement_mode": "auto",
        "settlement_timing_hint": "same_day_or_t+1",
    },
    "naverpay": {
        "provider": "naverpay",
        "provider_display": "Naver Pay",
        "fee_hint_bps": 220,
        "settlement_mode": "auto",
        "settlement_timing_hint": "t+1_business_days",
    },
    "kakaopay": {
        "provider": "kakaopay",
        "provider_display": "Kakao Pay",
        "fee_hint_bps": 250,
        "settlement_mode": "auto",
        "settlement_timing_hint": "t+1_business_days",
    },
    "payco": {
        "provider": "payco",
        "provider_display": "Payco",
        "fee_hint_bps": 240,
        "settlement_mode": "auto",
        "settlement_timing_hint": "t+1_business_days",
    },
    "bank_transfer": {
        "provider": "bank_transfer",
        "provider_display": "Bank Transfer",
        "fee_hint_bps": 0,
        "settlement_mode": "manual",
        "settlement_timing_hint": "manual_confirmation_required",
    },
}


def payment_method_profile(method: str | None) -> dict:
    normalized = (method or "card").strip().lower()
    return _METHOD_PROFILES.get(normalized, _METHOD_PROFILES["card"]).copy()


def payment_settlement_state(method: str | None, status: str | None) -> str:
    normalized_method = (method or "card").strip().lower()
    normalized_status = (status or "pending").strip().lower()
    if normalized_status == "completed":
        return "settled_manual" if normalized_method == "bank_transfer" else "settled"
    if normalized_status == "failed":
        return "settlement_failed"
    if normalized_status == "cancelled":
        return "voided"
    if normalized_method == "bank_transfer":
        return "awaiting_deposit"
    return "awaiting_settlement"


def build_payment_metadata(
    method: str | None,
    status: str | None,
    external_ref: str | None,
) -> dict:
    profile = payment_method_profile(method)
    fee_hint_bps = int(profile.get("fee_hint_bps") or 0)
    return {
        "provider": profile["provider"],
        "provider_display": profile["provider_display"],
        "provider_reference": external_ref,
        "fee_hint_bps": fee_hint_bps,
        "fee_hint_label": f"{fee_hint_bps / 100:.2f}%",
        "settlement_mode": profile["settlement_mode"],
        "settlement_timing_hint": profile["settlement_timing_hint"],
        "settlement_state": payment_settlement_state(method, status),
    }
