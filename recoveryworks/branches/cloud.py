"""CloudRecovery contracted-rate and metered-usage billing audit."""
from __future__ import annotations

from typing import Iterable

from recoveryworks.models import Branch
from .contract_billing import (
    ContractBillingBatch,
    ContractRate,
    InvoiceCharge,
    UsageRecord,
    audit_contract_billing,
)


def audit_cloud_billing(
    *,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    usage: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    """Compare provider charges to effective contracted cloud/hosting pricing.

    Unit pricing is intentionally generic: compute-hours, GB-months, requests,
    vCPU-hours, seats, or another reviewed billing unit are supported when the
    contract and independent usage export use the same unit.
    """
    return audit_contract_billing(
        branch=Branch.CLOUD,
        client_id=client_id,
        charges=charges,
        rates=rates,
        usage=usage,
        currency=currency,
    )
