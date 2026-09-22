"""Payroll/BenefitBillingRecovery employer-side vendor billing audit."""
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


def audit_payroll_benefit_billing(
    *,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    units: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    """Audit employer-side payroll-service and benefit-carrier billing.

    This branch is for vendor/carrier invoice reconciliation only. It does not
    calculate employee wages, payroll taxes, employee deductions, benefits
    eligibility, or employee claims.
    """
    return audit_contract_billing(
        branch=Branch.PAYROLL_BENEFIT,
        client_id=client_id,
        charges=charges,
        rates=rates,
        usage=units,
        currency=currency,
    )
