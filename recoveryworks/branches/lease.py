"""LeaseRecovery recurring rent/CAM/area-based billing audit."""
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


def audit_lease_billing(
    *,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    area: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    """Compare landlord charges with effective lease pricing.

    ContractRate.fixed_cents represents fixed rent/CAM components.
    ContractRate.unit_rate_micros may represent a charge per independently
    supplied allocation unit, commonly square feet. Area records are independent
    quantity evidence keyed to Charge_ID.
    """
    return audit_contract_billing(
        branch=Branch.LEASE,
        client_id=client_id,
        charges=charges,
        rates=rates,
        usage=area,
        currency=currency,
    )
