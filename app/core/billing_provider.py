"""
Billing Provider Adapter

Abstract interface for billing providers. Core subscription logic
never touches payment details — it delegates to a provider adapter.

To add a new provider:
1. Subclass BillingProvider
2. Implement verify_payment() and process_renewal()
3. Register in BILLING_PROVIDERS dict
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PaymentResult:
    success: bool
    reference: str
    error: Optional[str] = None


@dataclass
class RenewResult:
    success: bool
    reference: Optional[str] = None
    error: Optional[str] = None
    extended_days: int = 0


class BillingProvider(ABC):
    """Abstract billing provider interface."""

    @abstractmethod
    async def verify_payment(self, reference: str) -> PaymentResult:
        """Verify that a payment reference is valid and paid."""
        ...

    @abstractmethod
    async def process_renewal(self, subscription_id: int, user_id: int) -> RenewResult:
        """Attempt to renew a subscription via this provider."""
        ...


class ManualBillingProvider(BillingProvider):
    """
    Default provider — admin/manual payments.
    Payment is always considered valid (admin responsibility).
    Renewal requires manual re-payment.
    """

    async def verify_payment(self, reference: str) -> PaymentResult:
        logger.info(f"💳 [BILLING:MANUAL] Verifying payment ref={reference} (auto-approved)")
        return PaymentResult(success=True, reference=reference)

    async def process_renewal(self, subscription_id: int, user_id: int) -> RenewResult:
        logger.info(f"💳 [BILLING:MANUAL] Auto-renewal not supported for manual billing (sub={subscription_id})")
        return RenewResult(
            success=False,
            error="Manual billing does not support auto-renewal",
            extended_days=0,
        )


# ============ PROVIDER REGISTRY ============
# Add new providers here. Key = billing_provider column value.

BILLING_PROVIDERS: dict[str, BillingProvider] = {
    "manual": ManualBillingProvider(),
}


def get_billing_provider(provider_name: Optional[str]) -> BillingProvider:
    """Get a billing provider by name. Falls back to manual."""
    if not provider_name:
        return BILLING_PROVIDERS["manual"]
    return BILLING_PROVIDERS.get(provider_name, BILLING_PROVIDERS["manual"])
