"""Warranty/CreditRecovery supplier credit entitlement reconciliation."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def normalize_credit_category(value: str) -> str:
    return _required("credit_category", value).upper().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class WarrantyCreditEntitlement:
    entitlement_id: str
    client_id: str
    supplier_id: str
    reference_id: str
    credit_category: str
    entitled_cents: int
    effective_date: str
    entitlement_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    entitlement_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "entitlement_id", "client_id", "supplier_id", "reference_id",
            "credit_category", "effective_date", "entitlement_basis",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        normalize_credit_category(self.credit_category)
        _iso_date("effective_date", self.effective_date)
        _cents("entitled_cents", self.entitled_cents)
        if self.entitled_cents <= 0:
            raise ValueError("entitled_cents must be positive")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.verified and not (
            isinstance(self.entitlement_reviewer_id, str)
            and self.entitlement_reviewer_id.strip()
        ):
            raise ValueError(
                "verified warranty/credit entitlement requires entitlement_reviewer_id"
            )

    @property
    def normalized_category(self) -> str:
        return normalize_credit_category(self.credit_category)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "entitlement_id": self.entitlement_id,
            "client_id": self.client_id,
            "supplier_id": self.supplier_id,
            "reference_id": self.reference_id,
            "credit_category": self.normalized_category,
            "entitled_cents": self.entitled_cents,
            "effective_date": self.effective_date,
            "entitlement_basis": self.entitlement_basis,
            "source_hash": self.source_hash,
            "entitlement_reviewer_id": self.entitlement_reviewer_id,
        }
        return RuleRef(
            rule_id="warranty-credit-entitlement:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_date,
            effective_to=None,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "reviewed_warranty_credit_entitlement",
                "supplier_id": self.supplier_id,
                "reference_id": self.reference_id,
                "credit_category": self.normalized_category,
                "entitled_cents": self.entitled_cents,
                "entitlement_basis": self.entitlement_basis,
                "entitlement_reviewer_id": self.entitlement_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class WarrantyCreditSettlement:
    settlement_id: str
    entitlement_id: str
    amount_received_cents: int
    settlement_date: str
    source_hash: str
    source_locator: str
    verified: bool
    settlement_kind: str = "CREDIT_MEMO"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "settlement_id", "entitlement_id", "settlement_date",
            "source_hash", "source_locator", "settlement_kind",
        ):
            _required(name, getattr(self, name))
        _iso_date("settlement_date", self.settlement_date)
        _cents("amount_received_cents", self.amount_received_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"warranty-credit-settlement:{self.settlement_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="warranty_credit_settlement",
            verified=self.verified,
            metadata={
                "entitlement_id": self.entitlement_id,
                "amount_received_cents": self.amount_received_cents,
                "settlement_date": self.settlement_date,
                "settlement_kind": self.settlement_kind,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class WarrantyCreditAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class WarrantyCreditAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[WarrantyCreditAuditException, ...]


def audit_warranty_credits(
    *,
    client_id: str,
    entitlements: Iterable[WarrantyCreditEntitlement],
    settlements: Iterable[WarrantyCreditSettlement],
    currency: str = "USD",
) -> WarrantyCreditAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    entitlement_groups: dict[str, list[WarrantyCreditEntitlement]] = defaultdict(list)
    for entitlement in entitlements:
        entitlement_groups[entitlement.entitlement_id].append(entitlement)

    settlement_groups: dict[str, list[WarrantyCreditSettlement]] = defaultdict(list)
    settlement_ids: dict[str, int] = defaultdict(int)
    for settlement in settlements:
        settlement_groups[settlement.entitlement_id].append(settlement)
        settlement_ids[settlement.settlement_id] += 1
    duplicate_settlement_ids = {
        settlement_id for settlement_id, count in settlement_ids.items() if count > 1
    }

    observations: list[RecoveryObservation] = []
    exceptions: list[WarrantyCreditAuditException] = []

    for settlement_id in sorted(duplicate_settlement_ids):
        exceptions.append(WarrantyCreditAuditException(
            settlement_id,
            "DUPLICATE_CREDIT_SETTLEMENT_ID",
            "duplicate settlement ID prevents reliable received-credit calculation",
        ))

    for entitlement_id in sorted(entitlement_groups):
        values = entitlement_groups[entitlement_id]
        if len(values) != 1:
            exceptions.append(WarrantyCreditAuditException(
                entitlement_id,
                "DUPLICATE_CREDIT_ENTITLEMENT_ID",
                f"entitlement_id appears {len(values)} times; excluded",
            ))
            continue
        entitlement = values[0]
        if entitlement.client_id != client_id:
            exceptions.append(WarrantyCreditAuditException(
                entitlement_id,
                "CLIENT_SCOPE_MISMATCH",
                "entitlement client_id does not match Scan 360 client_id",
            ))
            continue

        group_settlements = settlement_groups.get(entitlement_id, [])
        if any(
            settlement.settlement_id in duplicate_settlement_ids
            for settlement in group_settlements
        ):
            exceptions.append(WarrantyCreditAuditException(
                entitlement_id,
                "ENTITLEMENT_BLOCKED_BY_DUPLICATE_SETTLEMENT",
                "duplicate settlement IDs prevent reliable actual credit amount",
            ))
            continue
        if not group_settlements:
            exceptions.append(WarrantyCreditAuditException(
                entitlement_id,
                "NO_CREDIT_SETTLEMENT_EVIDENCE",
                "actual credit/refund received cannot be established",
            ))
            continue

        actual_cents = sum(s.amount_received_cents for s in group_settlements)
        if entitlement.entitled_cents <= actual_cents:
            continue

        evidence = tuple(
            settlement.evidence()
            for settlement in sorted(
                group_settlements, key=lambda item: item.settlement_id
            )
        )
        observations.append(RecoveryObservation(
            branch=Branch.WARRANTY_CREDIT,
            client_id=client_id,
            counterparty_id=entitlement.supplier_id,
            reference=entitlement.entitlement_id,
            currency=currency,
            expected_cents=entitlement.entitled_cents,
            actual_cents=actual_cents,
            rule=entitlement.rule_ref(),
            evidence=evidence,
            reason="WARRANTY_OR_SUPPLIER_CREDIT_UNDERPAYMENT",
            confidence_basis=(
                "verified approved credit entitlement + verified settlement evidence"
                if entitlement.verified and all(ref.verified for ref in evidence)
                else "credit entitlement/settlement evidence requires verification"
            ),
            metadata={
                "reference_id": entitlement.reference_id,
                "credit_category": entitlement.normalized_category,
                "entitlement_basis": entitlement.entitlement_basis,
                "entitlement_reviewer_id": entitlement.entitlement_reviewer_id,
                "settlement_ids": [
                    settlement.settlement_id for settlement in group_settlements
                ],
            },
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    observations.sort(key=lambda x: (x.counterparty_id, x.reference))
    return WarrantyCreditAuditBatch(tuple(observations), tuple(exceptions))
