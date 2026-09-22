"""APRecovery reconciliation-kernel shadow mode.

Shadow mode is diagnostic only. It runs the shared reconciliation kernel beside
existing APRecovery logic and reports whether legacy recovery candidates leave
a corresponding payment-side residual. It never creates RecoveryObservations,
never changes finding state, and never authorizes or submits a recovery action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from recoveryworks.models import canonical_hash
from recoveryworks.reconciliation_kernel import (
    ManyToOneConfig,
    ReconConfig,
    ReconResult,
    ReconTxn,
    SOURCE_COMMIT,
    reconcile,
)

from .ap import (
    APObligation,
    APPayment,
    APRecoveryException,
    APVendorStatementLine,
    _dedupe_payment_ids,
    _obligation_index,
    audit_ap_recovery,
)


_SCOPED_LEGACY_REASONS = {
    "AP_OBLIGATION_OVERPAYMENT",
    "SUSPECTED_DUPLICATE_PAYMENT",
}


@dataclass(frozen=True)
class APShadowDiagnostic:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class APShadowLegacyCandidate:
    reference: str
    reason: str
    potential_recovery_cents: int


@dataclass(frozen=True)
class APReconciliationShadowReport:
    """Read-only comparison between existing AP logic and the shared kernel."""

    kernel_result: ReconResult
    legacy_candidates: tuple[APShadowLegacyCandidate, ...]
    legacy_exceptions: tuple[APRecoveryException, ...]
    exclusions: tuple[APShadowDiagnostic, ...]
    disagreements: tuple[APShadowDiagnostic, ...]
    kernel_matched_references: tuple[str, ...]
    kernel_residual_payment_references: tuple[str, ...]
    kernel_residual_obligation_references: tuple[str, ...]
    comparison_complete: bool
    kernel_source_commit: str = SOURCE_COMMIT


def _major_units(cents: int) -> str:
    if type(cents) is not int or cents < 0:
        raise ValueError("shadow AP amounts must be non-negative integer cents")
    whole, fraction = divmod(cents, 100)
    return f"{whole}.{fraction:02d}"


def _display_reference(key: tuple[str, str]) -> str:
    return f"{key[0]}/{key[1]}"


def _kernel_reference(key: tuple[str, str]) -> str:
    # Hash the namespace instead of passing raw vendor/invoice values through
    # reference normalization. The human-readable key is retained in the maps.
    return "APKEY-" + canonical_hash(
        {"vendor_id": key[0], "normalized_invoice": key[1]}
    )


def _payment_shadow_id(payment: APPayment) -> str:
    return "ap-shadow-payment:" + canonical_hash(
        {
            "vendor_id": payment.vendor_id,
            "normalized_invoice": payment.normalized_invoice,
            "payment_id": payment.payment_id,
            "source_hash": payment.source_hash,
            "source_locator": payment.source_locator,
        }
    )


def _obligation_shadow_id(obligation: APObligation) -> str:
    return "ap-shadow-obligation:" + canonical_hash(
        {
            "vendor_id": obligation.vendor_id,
            "normalized_invoice": obligation.normalized_invoice,
            "source_hash": obligation.source_hash,
            "source_locator": obligation.source_locator,
            "effective_from": obligation.effective_from,
        }
    )


def shadow_ap_reconciliation(
    *,
    client_id: str,
    payments: Iterable[APPayment],
    obligations: Iterable[APObligation] = (),
    statements: Iterable[APVendorStatementLine] = (),
    currency: str = "USD",
    date_window_days: int = 180,
) -> APReconciliationShadowReport:
    """Run the shared reconciliation kernel without affecting AP decisions.

    Existing APRecovery remains the authority for candidate detection. The
    kernel receives only deduplicated payment rows with real payment dates and
    the deduplicated obligation set. Vendor statement credits remain outside
    the kernel because they are entitlement/corroboration evidence, not a
    settlement row.

    A legacy AP recovery candidate is considered to have a kernel signal when
    at least one payment for the same vendor/invoice remains residual after
    reconciliation. A missing payment date makes that reference incomplete
    rather than a disagreement.
    """
    if type(date_window_days) is not int or date_window_days < 0:
        raise ValueError("date_window_days must be a non-negative integer")

    payment_rows = tuple(payments)
    obligation_rows = tuple(obligations)
    statement_rows = tuple(statements)

    legacy = audit_ap_recovery(
        client_id=client_id,
        payments=payment_rows,
        obligations=obligation_rows,
        statements=statement_rows,
        currency=currency,
    )
    accepted_payments, _ = _dedupe_payment_ids(payment_rows)
    obligation_by_key = _obligation_index(obligation_rows)

    internal: list[ReconTxn] = []
    settlement: list[ReconTxn] = []
    payment_key_by_id: dict[str, tuple[str, str]] = {}
    obligation_key_by_id: dict[str, tuple[str, str]] = {}
    exclusions: list[APShadowDiagnostic] = []
    incomplete_keys: set[tuple[str, str]] = set()

    for payment in accepted_payments:
        key = payment.key
        if payment.payment_date is None:
            incomplete_keys.add(key)
            exclusions.append(
                APShadowDiagnostic(
                    reference=_display_reference(key),
                    code="MISSING_PAYMENT_DATE_FOR_SHADOW",
                    detail=(
                        f"payment {payment.payment_id} has no payment_date; "
                        "excluded from reconciliation kernel rather than guessed"
                    ),
                )
            )
            continue
        shadow_id = _payment_shadow_id(payment)
        payment_key_by_id[shadow_id] = key
        internal.append(
            ReconTxn(
                id=shadow_id,
                amount=_major_units(payment.amount_cents),
                date=payment.payment_date,
                currency=currency,
                reference=_kernel_reference(key),
                metadata={
                    "vendor_id": payment.vendor_id,
                    "normalized_invoice": payment.normalized_invoice,
                    "payment_id": payment.payment_id,
                    "source_hash": payment.source_hash,
                    "source_locator": payment.source_locator,
                },
            )
        )

    for key in sorted(obligation_by_key):
        obligation = obligation_by_key[key]
        shadow_id = _obligation_shadow_id(obligation)
        obligation_key_by_id[shadow_id] = key
        settlement.append(
            ReconTxn(
                id=shadow_id,
                amount=_major_units(obligation.expected_cents),
                date=obligation.effective_from,
                currency=currency,
                reference=_kernel_reference(key),
                metadata={
                    "vendor_id": obligation.vendor_id,
                    "normalized_invoice": obligation.normalized_invoice,
                    "source_hash": obligation.source_hash,
                    "source_locator": obligation.source_locator,
                },
            )
        )

    config = ReconConfig(
        date_window_days=date_window_days,
        amount_tolerance_bps=0,
        amount_tolerance_min_minor=0,
        many_to_one=ManyToOneConfig(
            enabled=True,
            date_window_days=date_window_days,
            tolerance_bps=0,
        ),
    )
    kernel_result = reconcile(internal, settlement, config)

    matched_keys: set[tuple[str, str]] = set()
    for group in kernel_result.matches:
        for obligation_id in group.settlement_ids:
            key = obligation_key_by_id.get(obligation_id)
            if key is not None:
                matched_keys.add(key)

    residual_payment_keys = {
        key
        for residual in kernel_result.unmatched_internal
        if (key := payment_key_by_id.get(residual.id)) is not None
    }
    residual_obligation_keys = {
        key
        for residual in kernel_result.unmatched_settlement
        if (key := obligation_key_by_id.get(residual.id)) is not None
    }

    legacy_candidates: list[APShadowLegacyCandidate] = []
    disagreements: list[APShadowDiagnostic] = []
    for observation in legacy.observations:
        if observation.reason not in _SCOPED_LEGACY_REASONS:
            continue
        key = (observation.counterparty_id, observation.reference)
        potential = max(observation.actual_cents - observation.expected_cents, 0)
        legacy_candidates.append(
            APShadowLegacyCandidate(
                reference=_display_reference(key),
                reason=observation.reason,
                potential_recovery_cents=potential,
            )
        )
        if key in incomplete_keys:
            continue
        if key not in residual_payment_keys:
            disagreements.append(
                APShadowDiagnostic(
                    reference=_display_reference(key),
                    code="LEGACY_CANDIDATE_WITHOUT_KERNEL_PAYMENT_RESIDUAL",
                    detail=(
                        "existing APRecovery produced an in-scope recovery candidate, "
                        "but the reconciliation kernel consumed all dated payment rows "
                        "for this vendor/invoice"
                    ),
                )
            )

    return APReconciliationShadowReport(
        kernel_result=kernel_result,
        legacy_candidates=tuple(
            sorted(legacy_candidates, key=lambda item: (item.reference, item.reason))
        ),
        legacy_exceptions=legacy.exceptions,
        exclusions=tuple(
            sorted(exclusions, key=lambda item: (item.reference, item.code, item.detail))
        ),
        disagreements=tuple(
            sorted(disagreements, key=lambda item: (item.reference, item.code))
        ),
        kernel_matched_references=tuple(
            sorted(_display_reference(key) for key in matched_keys)
        ),
        kernel_residual_payment_references=tuple(
            sorted(_display_reference(key) for key in residual_payment_keys)
        ),
        kernel_residual_obligation_references=tuple(
            sorted(_display_reference(key) for key in residual_obligation_keys)
        ),
        comparison_complete=not incomplete_keys,
    )
