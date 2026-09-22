"""SaaSRecovery contract-rate and seat-billing audit."""
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


def audit_saas_billing(
    *,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    usage: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    return audit_contract_billing(
        branch=Branch.SAAS,
        client_id=client_id,
        charges=charges,
        rates=rates,
        usage=usage,
        currency=currency,
    )
