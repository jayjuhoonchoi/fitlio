from dataclasses import dataclass


@dataclass
class DispatchResult:
    delivered: bool
    provider_message_id: str | None = None
    error: str | None = None


def deliver_inapp(*, recipient_id: int | None, message: str) -> DispatchResult:
    if recipient_id is None:
        return DispatchResult(delivered=False, error="inapp requires recipient_id")
    return DispatchResult(delivered=True, provider_message_id=f"inapp-{recipient_id}")


def deliver_email(*, to_email: str | None, message: str) -> DispatchResult:
    if not to_email:
        return DispatchResult(delivered=False, error="email address missing")
    return DispatchResult(delivered=True, provider_message_id=f"email-{to_email}")


def deliver_sms(*, to_phone: str | None, message: str) -> DispatchResult:
    if not to_phone:
        return DispatchResult(delivered=False, error="phone number missing")
    return DispatchResult(delivered=True, provider_message_id=f"sms-{to_phone[-4:]}")
