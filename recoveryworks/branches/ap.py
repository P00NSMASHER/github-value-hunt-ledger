"""APRecovery ingestion and deterministic recovery detection.

The adapter consumes concrete payment, obligation, and vendor-statement records.
It is intentionally conservative:
- verified obligation + verified payments can produce VALIDATED overpayments;
- a verified negative vendor-statement balance can produce a validated credit;
- duplicate-looking payments without verified authority stay REVIEW;
- duplicate payment IDs and contradictory statement evidence fail closed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
import re
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


_SUFFIX = re.compile(r"[-_]?(R|DUP|COPY|REV|REVERSAL)[-_]?$", re.IGNORECASE)


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _positive_cents(name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive integer cents")
    return value


def _signed_cents(name: str, value: int) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be integer cents")
    return value


def _iso_date(name: str, value: str) -> str:
    text = _required(name, value)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    return text


def canonical_invoice_number(value: str) -> str:
    """Canonicalize formatting only; never change the invoice's semantic ID."""
    return _required("invoice_number", value).upper().replace(" ", "")


def normalize_invoice_number(value: str) -> str:
    """Return a heuristic invoice family for duplicate discovery only.

    Known reversal/copy suffixes are stripped so suspicious relationships can be
    surfaced, but RecoveryOS must not treat this heuristic family as proof that
    two invoice IDs are the same obligation.
    """
    return _SUFFIX.sub("", canonical_invoice_number(value))


@dataclass(frozen=True)
class APPayment:
    payment_id: str
    vendor_id: str
    invoice_number: str
    amount_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    payment_date: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("payment_id", "vendor_id", "invoice_number", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _positive_cents("amount_cents", self.amount_cents)
        if self.payment_date is not None:
            _iso_date("payment_date", self.payment_date)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def canonical_invoice(self) -> str:
        return canonical_invoice_number(self.invoice_number)

    @property
    def normalized_invoice(self) -> str:
        return normalize_invoice_number(self.invoice_number)

    @property
    def key(self) -> tuple[str, str]:
        """Heuristic family key used only to discover possible duplicate clusters."""
        return (self.vendor_id, self.normalized_invoice)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"ap-payment:{self.payment_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="ap_payment",
            verified=self.verified,
            metadata={
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "payment_date": self.payment_date,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class APObligation:
    vendor_id: str
    invoice_number: str
    expected_cents: int
    source_hash: str
    source_locator: str
    effective_from: str
    verified: bool
    effective_to: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "vendor_id", "invoice_number", "source_hash",
            "source_locator", "effective_from",
        ):
            _required(name, getattr(self, name))
        _positive_cents("expected_cents", self.expected_cents)
        start = date.fromisoformat(_iso_date("effective_from", self.effective_from))
        if self.effective_to is not None:
            end = date.fromisoformat(_iso_date("effective_to", self.effective_to))
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def canonical_invoice(self) -> str:
        return canonical_invoice_number(self.invoice_number)

    @property
    def normalized_invoice(self) -> str:
        return normalize_invoice_number(self.invoice_number)

    @property
    def key(self) -> tuple[str, str]:
        """Exact obligation identity; heuristic suffix folding is not authority."""
        return (self.vendor_id, self.canonical_invoice)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "vendor_id": self.vendor_id,
            "invoice_number": self.canonical_invoice,
            "expected_cents": self.expected_cents,
            "source_hash": self.source_hash,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
        }
        return RuleRef(
            rule_id="ap-obligation:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "ap_obligation",
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "expected_cents": self.expected_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class APVendorStatementLine:
    """One invoice-level vendor statement balance.

    Negative balance means the vendor reports a credit owed to the client.
    Positive balance means the vendor reports an amount still due.
    """

    vendor_id: str
    invoice_number: str
    balance_cents: int
    statement_date: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("vendor_id", "invoice_number", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _signed_cents("balance_cents", self.balance_cents)
        _iso_date("statement_date", self.statement_date)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def canonical_invoice(self) -> str:
        return canonical_invoice_number(self.invoice_number)

    @property
    def normalized_invoice(self) -> str:
        return normalize_invoice_number(self.invoice_number)

    @property
    def key(self) -> tuple[str, str]:
        """Exact vendor-statement invoice identity."""
        return (self.vendor_id, self.canonical_invoice)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="ap-statement:" + canonical_hash({
                "vendor_id": self.vendor_id,
                "invoice_number": self.canonical_invoice,
                "statement_date": self.statement_date,
                "source_hash": self.source_hash,
                "locator": self.source_locator,
            }),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="vendor_statement",
            verified=self.verified,
            metadata={
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "statement_date": self.statement_date,
                "balance_cents": self.balance_cents,
                **dict(self.metadata),
            },
        )

    def credit_rule_ref(self) -> RuleRef:
        if self.balance_cents >= 0:
            raise ValueError("vendor statement line is not a credit")
        identity = {
            "schema": 1,
            "vendor_id": self.vendor_id,
            "invoice_number": self.canonical_invoice,
            "statement_date": self.statement_date,
            "credit_cents": abs(self.balance_cents),
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="ap-statement-credit:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.statement_date,
            effective_to=None,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "vendor_statement_credit",
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "credit_cents": abs(self.balance_cents),
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class APRecoveryException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class APRecoveryBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[APRecoveryException, ...]


def _same_obligation(a: APObligation, b: APObligation) -> bool:
    """Treat repeated rows from the same source export as one obligation."""
    return (
        a.key == b.key
        and a.expected_cents == b.expected_cents
        and a.source_hash == b.source_hash
        and a.effective_from == b.effective_from
        and a.effective_to == b.effective_to
        and a.verified == b.verified
    )


def _obligation_index(obligations: Iterable[APObligation]) -> dict[tuple[str, str], APObligation]:
    result: dict[tuple[str, str], APObligation] = {}
    for obligation in obligations:
        existing = result.get(obligation.key)
        if existing is None:
            result[obligation.key] = obligation
            continue
        if _same_obligation(existing, obligation):
            continue
        raise ValueError(
            "conflicting AP obligations for "
            f"{obligation.vendor_id}/{obligation.normalized_invoice}"
        )
    return result


def _dedupe_payment_ids(
    payments: Iterable[APPayment],
) -> tuple[tuple[APPayment, ...], tuple[APRecoveryException, ...]]:
    """Deduplicate repeated export lines without rejecting split-settlement payments.

    One ACH/check can legitimately repeat the same payment_id across several
    invoices. The collision boundary is therefore vendor + exact canonical
    invoice + payment_id. Heuristic suffix folding is never used to deduplicate
    source rows. Repeated identical lines collapse to one; conflicting lines are
    excluded and surfaced for review.
    """
    grouped: dict[tuple[str, str, str], list[APPayment]] = defaultdict(list)
    for payment in payments:
        grouped[(payment.vendor_id, payment.canonical_invoice, payment.payment_id)].append(payment)

    accepted: list[APPayment] = []
    exceptions: list[APRecoveryException] = []
    for key in sorted(grouped):
        items = grouped[key]
        if len(items) == 1:
            accepted.append(items[0])
            continue

        signatures = {
            (item.amount_cents, item.payment_date, item.source_hash, item.verified)
            for item in items
        }
        reference = f"{key[0]}/{key[1]}/{key[2]}"
        if len(signatures) == 1:
            accepted.append(sorted(items, key=lambda item: item.source_locator)[0])
            exceptions.append(APRecoveryException(
                reference,
                "DUPLICATE_PAYMENT_ID",
                f"payment line appears {len(items)} times in the source export; counted once",
            ))
            continue

        exceptions.append(APRecoveryException(
            reference,
            "CONFLICTING_PAYMENT_ID",
            "same vendor/invoice/payment_id has conflicting amount/date/source attributes; excluded from recovery math",
        ))

    return tuple(accepted), tuple(exceptions)

def _latest_statement_index(
    statements: Iterable[APVendorStatementLine],
) -> tuple[dict[tuple[str, str], APVendorStatementLine], tuple[APRecoveryException, ...]]:
    grouped: dict[tuple[str, str], list[APVendorStatementLine]] = defaultdict(list)
    for item in statements:
        grouped[item.key].append(item)

    result: dict[tuple[str, str], APVendorStatementLine] = {}
    exceptions: list[APRecoveryException] = []
    for key in sorted(grouped):
        items = sorted(grouped[key], key=lambda x: (x.statement_date, x.source_locator))
        latest_date = items[-1].statement_date
        latest = [item for item in items if item.statement_date == latest_date]
        balances = {item.balance_cents for item in latest}
        if len(balances) > 1:
            reference = f"{key[0]}/{key[1]}"
            exceptions.append(APRecoveryException(
                reference,
                "CONFLICTING_VENDOR_STATEMENT_LINES",
                f"multiple balances exist for latest statement date {latest_date}",
            ))
            continue
        result[key] = latest[-1]
    return result, tuple(exceptions)


def _unverified_rule(rule: RuleRef) -> RuleRef:
    return replace(
        rule,
        verified_controlling=False,
        metadata={**dict(rule.metadata), "verification_downgrade": "contradictory_statement"},
    )


def audit_ap_recovery(
    *,
    client_id: str,
    payments: Iterable[APPayment],
    obligations: Iterable[APObligation] = (),
    statements: Iterable[APVendorStatementLine] = (),
    currency: str = "USD",
) -> APRecoveryBatch:
    """Audit AP records into proof-bound RecoveryObservations.

    Vendor statements are used in two ways:
    1. a matching negative credit can corroborate an obligation/payment overpay;
    2. a statement-only negative credit is itself a recovery candidate.

    A positive statement balance that contradicts a calculated overpayment does
    not erase the candidate, but it forces the candidate back to REVIEW.
    """
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    accepted_payments, payment_exceptions = _dedupe_payment_ids(payments)
    statement_by_key, statement_exceptions = _latest_statement_index(statements)
    exceptions = list(payment_exceptions) + list(statement_exceptions)

    statement_family_groups: dict[tuple[str, str], list[APVendorStatementLine]] = defaultdict(list)
    for statement_item in statement_by_key.values():
        statement_family_groups[
            (statement_item.vendor_id, statement_item.normalized_invoice)
        ].append(statement_item)
    statement_by_family = {
        family: items[0]
        for family, items in statement_family_groups.items()
        if len(items) == 1
    }

    payment_groups: dict[tuple[str, str], list[APPayment]] = defaultdict(list)
    for payment in accepted_payments:
        payment_groups[payment.key].append(payment)

    obligation_by_key = _obligation_index(obligations)
    observations: list[RecoveryObservation] = []
    represented_statement_keys: set[tuple[str, str]] = set()

    for key in sorted(payment_groups):
        vendor_id, normalized_invoice = key
        items = sorted(payment_groups[key], key=lambda p: p.payment_id)
        canonical_invoices = sorted({p.canonical_invoice for p in items})
        exact_key = (
            (vendor_id, canonical_invoices[0])
            if len(canonical_invoices) == 1
            else None
        )
        obligation = obligation_by_key.get(exact_key) if exact_key else None
        statement = statement_by_key.get(exact_key) if exact_key else None
        heuristic_alias_group = len(canonical_invoices) > 1
        reference_invoice = canonical_invoices[0] if exact_key else normalized_invoice

        if heuristic_alias_group:
            exceptions.append(APRecoveryException(
                f"{vendor_id}/{normalized_invoice}",
                "HEURISTIC_INVOICE_ALIAS",
                "multiple exact invoice IDs collapse to one duplicate-discovery family; obligation authority matching is disabled",
            ))
            family_statements = statement_family_groups.get(key, [])
            if len(family_statements) > 1:
                exceptions.append(APRecoveryException(
                    f"{vendor_id}/{normalized_invoice}",
                    "AMBIGUOUS_STATEMENT_ALIAS_FAMILY",
                    "multiple exact vendor-statement invoice IDs share the same heuristic family; duplicate inference is suppressed",
                ))
                # Exact statement credits, if any, are emitted separately below.
                continue

            family_statement = statement_by_family.get(key)
            if family_statement is not None:
                if family_statement.balance_cents < 0:
                    credit_cents = abs(family_statement.balance_cents)
                    represented_statement_keys.add(family_statement.key)
                    observations.append(RecoveryObservation(
                        branch=Branch.AP,
                        client_id=client_id,
                        counterparty_id=vendor_id,
                        reference=f"{family_statement.canonical_invoice}:statement-credit",
                        currency=currency,
                        expected_cents=0,
                        actual_cents=credit_cents,
                        rule=family_statement.credit_rule_ref(),
                        evidence=(family_statement.evidence(),),
                        reason="VENDOR_STATEMENT_CREDIT",
                        confidence_basis=(
                            "vendor statement credit is authoritative; suffix-normalized payment cluster is context only"
                            if family_statement.verified
                            else "vendor statement requires verification; suffix-normalized payment cluster is context only"
                        ),
                        metadata={
                            "normalized_invoice": normalized_invoice,
                            "canonical_invoice_number": family_statement.canonical_invoice,
                            "statement_date": family_statement.statement_date,
                            "statement_credit_cents": credit_cents,
                            "context_payment_ids": [p.payment_id for p in items],
                            "context_invoice_numbers": canonical_invoices,
                            "detection_basis": "vendor_statement_credit_with_heuristic_duplicate_context",
                        },
                    ))
                    continue

                exceptions.append(APRecoveryException(
                    f"{vendor_id}/{normalized_invoice}",
                    "STATEMENT_CONTRADICTS_HEURISTIC_DUPLICATE",
                    "vendor statement shows no credit for a suffix-normalized duplicate family; duplicate inference is suppressed",
                ))
                continue

        if obligation is not None:
            actual_cents = sum(p.amount_cents for p in items)
            if actual_cents <= obligation.expected_cents:
                continue
            recovery_cents = actual_cents - obligation.expected_cents
            evidence = [p.evidence() for p in items]
            rule = obligation.rule_ref()
            confidence = (
                "verified obligation and payment evidence"
                if obligation.verified and all(p.verified for p in items)
                else "obligation/payment evidence requires verification"
            )
            metadata: dict[str, Any] = {
                "normalized_invoice": normalized_invoice,
                "canonical_invoice_numbers": canonical_invoices,
                "payment_ids": [p.payment_id for p in items],
                "payment_count": len(items),
                "detection_basis": "obligation_vs_total_payments",
            }

            if statement is not None:
                represented_statement_keys.add(statement.key)
                evidence.append(statement.evidence())
                metadata["vendor_statement_balance_cents"] = statement.balance_cents
                metadata["vendor_statement_date"] = statement.statement_date
                if statement.balance_cents > 0:
                    exceptions.append(APRecoveryException(
                        f"{vendor_id}/{normalized_invoice}",
                        "STATEMENT_CONTRADICTS_OVERPAYMENT",
                        "vendor statement shows amount due while ledger math shows overpayment",
                    ))
                    rule = _unverified_rule(rule)
                    confidence = "contradictory vendor statement requires human reconciliation"
                elif statement.balance_cents < 0:
                    statement_credit = abs(statement.balance_cents)
                    matches = statement_credit == recovery_cents
                    metadata["statement_credit_cents"] = statement_credit
                    metadata["statement_credit_matches_recovery"] = matches
                    if not matches:
                        exceptions.append(APRecoveryException(
                            f"{vendor_id}/{normalized_invoice}",
                            "STATEMENT_CREDIT_MISMATCH",
                            "vendor statement credit does not equal calculated overpayment",
                        ))
                        rule = _unverified_rule(rule)
                        confidence = "vendor statement credit amount conflicts with ledger recovery math"

            observations.append(RecoveryObservation(
                branch=Branch.AP,
                client_id=client_id,
                counterparty_id=vendor_id,
                reference=reference_invoice,
                currency=currency,
                expected_cents=obligation.expected_cents,
                actual_cents=actual_cents,
                rule=rule,
                evidence=tuple(evidence),
                reason="AP_OBLIGATION_OVERPAYMENT",
                confidence_basis=confidence,
                metadata=metadata,
            ))
            continue

        by_amount: dict[int, list[APPayment]] = defaultdict(list)
        for payment in items:
            by_amount[payment.amount_cents].append(payment)

        for amount_cents in sorted(by_amount):
            duplicates = sorted(by_amount[amount_cents], key=lambda p: p.payment_id)
            if len(duplicates) < 2:
                continue
            recovery_cents = amount_cents * (len(duplicates) - 1)
            evidence = [p.evidence() for p in duplicates]
            rule = None
            confidence = (
                "same vendor + normalized invoice + exact payment amount; "
                "verified obligation still required"
            )
            reason = "SUSPECTED_DUPLICATE_PAYMENT"
            metadata: dict[str, Any] = {
                "normalized_invoice": normalized_invoice,
                "canonical_invoice_numbers": sorted({p.canonical_invoice for p in duplicates}),
                "payment_ids": [p.payment_id for p in duplicates],
                "payment_count": len(duplicates),
                "duplicate_amount_cents": amount_cents,
                "detection_basis": "exact_invoice_amount_duplicate",
            }
            if (
                statement is not None
                and statement.balance_cents < 0
                and not heuristic_alias_group
            ):
                represented_statement_keys.add(statement.key)
                evidence.append(statement.evidence())
                statement_credit = abs(statement.balance_cents)
                metadata["vendor_statement_date"] = statement.statement_date
                metadata["statement_credit_cents"] = statement_credit
                metadata["statement_credit_matches_recovery"] = (
                    statement_credit == recovery_cents
                )
                if statement_credit == recovery_cents:
                    rule = statement.credit_rule_ref()
                    reason = "VENDOR_STATEMENT_CONFIRMED_DUPLICATE_PAYMENT"
                    confidence = (
                        "exact duplicate payment cluster corroborated by vendor statement credit"
                    )
                else:
                    exceptions.append(APRecoveryException(
                        f"{vendor_id}/{normalized_invoice}",
                        "STATEMENT_CREDIT_MISMATCH",
                        "vendor statement credit does not equal suspected duplicate recovery",
                    ))
                    confidence = "duplicate cluster conflicts with vendor statement credit amount"

            observations.append(RecoveryObservation(
                branch=Branch.AP,
                client_id=client_id,
                counterparty_id=vendor_id,
                reference=f"{reference_invoice}:{amount_cents}",
                currency=currency,
                expected_cents=amount_cents,
                actual_cents=amount_cents * len(duplicates),
                rule=rule,
                evidence=tuple(evidence),
                reason=reason,
                confidence_basis=confidence,
                metadata=metadata,
            ))

    for key in sorted(statement_by_key):
        if key in represented_statement_keys:
            continue
        statement = statement_by_key[key]
        if statement.balance_cents >= 0:
            continue
        credit_cents = abs(statement.balance_cents)
        observations.append(RecoveryObservation(
            branch=Branch.AP,
            client_id=client_id,
            counterparty_id=statement.vendor_id,
            reference=f"{statement.canonical_invoice}:statement-credit",
            currency=currency,
            expected_cents=0,
            actual_cents=credit_cents,
            rule=statement.credit_rule_ref(),
            evidence=(statement.evidence(),),
            reason="VENDOR_STATEMENT_CREDIT",
            confidence_basis=(
                "verified vendor statement credit"
                if statement.verified else "vendor statement requires verification"
            ),
            metadata={
                "normalized_invoice": statement.normalized_invoice,
                "canonical_invoice_number": statement.canonical_invoice,
                "statement_date": statement.statement_date,
                "statement_credit_cents": credit_cents,
                "detection_basis": "vendor_statement_negative_balance",
            },
        ))

    observations.sort(key=lambda item: (item.counterparty_id, item.reference))
    exceptions.sort(key=lambda item: (item.code, item.reference, item.detail))
    return APRecoveryBatch(tuple(observations), tuple(exceptions))


def build_ap_observations(
    *,
    client_id: str,
    payments: Iterable[APPayment],
    obligations: Iterable[APObligation] = (),
    statements: Iterable[APVendorStatementLine] = (),
    currency: str = "USD",
) -> tuple[RecoveryObservation, ...]:
    """Backward-compatible observation-only wrapper."""
    return audit_ap_recovery(
        client_id=client_id,
        payments=payments,
        obligations=obligations,
        statements=statements,
        currency=currency,
    ).observations
