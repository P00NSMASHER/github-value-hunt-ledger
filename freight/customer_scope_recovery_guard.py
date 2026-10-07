"""Explicit customer/source invoice scope guard for SYNTHETIC RecoveryOS tests only.

A SHA256 checksum is reproducibility evidence, NOT a real e-signature,
customer ownership certificate, or consent to contact an actual carrier.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from freight.customer_lifecycle_product_probe import (
    SyntheticCustomerCase,
    run_synthetic_customer_case,
)

HASH = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class FictionalScopeBinding:
    scenario_id: str
    customer_id: str
    source_customer_id: str
    carrier_id: str
    invoice_id: str
    evidence_sha256: str
    consent_reference: str
    valid_from: int
    valid_until: int
    revoked_at: int | None
    checksum: str


def issue_fictional_binding(*, scenario_id: str, customer_id: str,
                            source_customer_id: str, carrier_id: str,
                            invoice_id: str, evidence_sha256: str,
                            consent_reference: str, valid_from: int,
                            valid_until: int, revoked_at: int | None = None
                            ) -> FictionalScopeBinding:
    body = locals().copy()
    if not re.fullmatch(r"SC-\d{7}", scenario_id):
        raise ValueError("only fictional scenario identifiers accepted")
    if not re.fullmatch(r"FCUST-\d{5}", customer_id):
        raise ValueError("only fictional customer identifiers accepted")
    if not re.fullmatch(r"CUSTOMER-\d{4}", source_customer_id):
        raise ValueError("only fictional source-account identifiers accepted")
    if not invoice_id.startswith("INV-") or not carrier_id.startswith("FICTIONAL-"):
        raise ValueError("only fictional invoice and carrier accepted")
    if not HASH.fullmatch(evidence_sha256):
        raise ValueError("source artifact hash missing")
    if not consent_reference.startswith("SYNTH-APPROVED-"):
        raise ValueError("fictional authorization reference required")
    if type(valid_from) is not int or type(valid_until) is not int or not (0 <= valid_from < valid_until):
        raise ValueError("invalid authority date interval")
    if revoked_at is not None and (type(revoked_at) is not int or revoked_at < valid_from):
        raise ValueError("invalid revocation")
    checksum = sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return FictionalScopeBinding(**body,checksum=checksum)


def guard_fictional_customer_scope(case: SyntheticCustomerCase,
                                   binding: FictionalScopeBinding | None,
                                   *, at_minute: int) -> None:
    if binding is None:
        raise ValueError("synthetic freight source-owner binding is absent")
    if not (binding.scenario_id == case.scenario_id and
            binding.customer_id == case.customer_id and
            binding.invoice_id == case.invoice_id and
            binding.carrier_id == case.carrier_id and
            binding.evidence_sha256 == case.source_sha256):
        raise ValueError("synthetic customer/invoice/source scope mismatch")
    if not binding.consent_reference.startswith("SYNTH-APPROVED-"):
        raise ValueError("synthetic consent reference is absent")
    if not binding.valid_from <= at_minute < binding.valid_until:
        raise ValueError("synthetic authority expired or not effective")
    if binding.revoked_at is not None and at_minute >= binding.revoked_at:
        raise ValueError("synthetic authority revoked")
    body = {k:v for k,v in vars(binding).items() if k!="checksum"}
    if sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=binding.checksum:
        raise ValueError("synthetic binding checksum changed")
    if not case.contract_accepted or not case.claim_authorized or case.authorization_revoked:
        raise ValueError("synthetic contractual or claim mandate prerequisite absent")


def run_guarded_synthetic_customer_case(case: SyntheticCustomerCase,
                                        binding: FictionalScopeBinding,
                                        *, at_minute: int,
                                        provider_states: tuple[str,...]=(
                                            "SUBMITTED","ACCEPTED","SETTLED")):
    guard_fictional_customer_scope(case,binding,at_minute=at_minute)
    return run_synthetic_customer_case(case,provider_states)
