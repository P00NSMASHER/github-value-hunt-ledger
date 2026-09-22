"""ProcurementRecovery contract/PO unit-price audit."""
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


def audit_procurement_billing(
    *,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    quantities: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    """Compare supplier invoice charges to effective contracted unit pricing.

    Shared ContractRate.unit_rate_micros represents the negotiated price per
    independent quantity unit. Fixed components are also supported for fees that
    are explicitly contracted. Quantity evidence should come from PO receipt,
    receiving, consumption, or another customer-controlled source rather than
    the supplier invoice itself.
    """
    return audit_contract_billing(
        branch=Branch.PROCUREMENT,
        client_id=client_id,
        charges=charges,
        rates=rates,
        usage=quantities,
        currency=currency,
    )
