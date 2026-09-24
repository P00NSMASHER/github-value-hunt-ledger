"""Bridge existing FreightRecovery authority assets into RecoveryOS RuleRef/EvidenceRef.

This module does not interpret contracts or scrape tariffs. It consumes the two
authority planes already implemented in this repository:

1. freight.finding_factory.ChargeRule — buyer-scoped normalized contract/rate rule.
2. production/fmc_tariff_ledger shipment authority envelope — exact-lane,
   effective-date, provenance-preserving FMC tariff context.

A ChargeRule remains the money-bearing controlling rule. The FMC envelope is an
additional applicability/provenance gate when supplied; public benchmark rows
never become controlling authority here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping

from freight.finding_factory import ChargeRule
from recoveryworks.models import EvidenceRef, RuleRef, canonical_hash

from .freight_audit_vendor import FindingType

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FreightAuthorityContext:
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    currency: str
    service_date: str
    charge_rules: tuple[ChargeRule, ...]
    fmc_envelope: Mapping[str, Any] | None = None
    fmc_organization_no: str | None = None
    origin: str | None = None
    destination: str | None = None
    container_type: str | None = None


@dataclass(frozen=True)
class FreightAuthorityResolution:
    rule: RuleRef | None
    evidence: tuple[EvidenceRef, ...]
    blockers: tuple[str, ...]
    matched_rule_hashes: tuple[str, ...]
    authority_hash: str


def _text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: str) -> str:
    return _text(value).upper()


def _norm_container(value: str) -> str:
    normalized = _norm(value).replace(" CONTAINER", "")
    return {
        "40HC": "40HQ",
        "20DRY": "20GP",
        "40DRY": "40GP",
    }.get(normalized, normalized)


def _iso_date(value: str) -> date:
    return date.fromisoformat(_text(value))


def _charge_codes(
    finding_type: FindingType,
    normalized_category: str | None,
) -> frozenset[str]:
    if normalized_category:
        category = _norm(normalized_category)
        aliases = {category}
        if category == "LINEHAUL":
            aliases.update({"BASE_RATE", "FREIGHT", "LINE_HAUL"})
        elif category == "FUEL":
            aliases.update({"FSC", "FUEL_SURCHARGE"})
        elif category == "DETENTION":
            aliases.update({"WAIT_TIME", "DRIVER_WAIT"})
        return frozenset(aliases)
    if finding_type is FindingType.TOTAL_MISMATCH:
        return frozenset({"TOTAL", "INVOICE_TOTAL", "BASE_RATE"})
    return frozenset()


def _rule_matches(
    rule: ChargeRule,
    context: FreightAuthorityContext,
    codes: frozenset[str],
) -> bool:
    try:
        service_day = _iso_date(context.service_date)
        start = _iso_date(rule.effective_from)
        end = _iso_date(rule.effective_to) if rule.effective_to else None
    except (TypeError, ValueError):
        return False

    if (
        (rule.buyer_id, rule.business_unit)
        != (context.buyer_id, context.business_unit)
    ):
        return False
    if (
        rule.customer_id,
        rule.carrier_id,
        _norm(rule.currency),
    ) != (
        context.customer_id,
        context.carrier_id,
        _norm(context.currency),
    ):
        return False
    if codes and _norm(rule.charge_code) not in codes:
        return False
    if not codes:
        return False
    return start <= service_day and (end is None or service_day <= end)


def _authority_document_evidence(rule: ChargeRule) -> tuple[EvidenceRef, ...]:
    digest = str(rule.document_source_hash or "").strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        return ()
    return (
        EvidenceRef(
            evidence_id=f"freight-authority-document:{digest}",
            source_hash=digest,
            locator=f"freight-authority://{rule.authority_document_id}",
            kind="freight_authority_document",
            verified=bool(rule.verified_controlling_authority),
            metadata={
                "authority_document_id": rule.authority_document_id,
                "charge_code": rule.charge_code,
                "rule_hash": rule.rule_hash,
            },
        ),
    )


def _hash_evidence(
    *,
    digest: str,
    locator: str,
    kind: str,
    metadata: Mapping[str, Any],
    verified: bool = True,
) -> EvidenceRef | None:
    value = str(digest or "").strip().lower()
    if not _SHA256_RE.fullmatch(value):
        return None
    return EvidenceRef(
        evidence_id=f"{kind}:{value}:{canonical_hash(dict(metadata))}",
        source_hash=value,
        locator=locator,
        kind=kind,
        verified=verified,
        metadata=metadata,
    )


def _fmc_source_evidence(
    envelope: Mapping[str, Any],
) -> tuple[EvidenceRef, ...]:
    out: list[EvidenceRef] = []
    seen: set[tuple[str, str]] = set()

    base = envelope.get("base_rate_authority") or {}
    for index, row in enumerate(base.get("contract_candidates") or []):
        if not isinstance(row, Mapping):
            continue
        for field, kind in (
            ("page_sha256", "freight_contract_rate_page"),
            ("query_response_sha256", "freight_contract_rate_query"),
        ):
            ref = _hash_evidence(
                digest=str(row.get(field) or ""),
                locator=str(
                    row.get("page_url")
                    or row.get("source_url")
                    or f"fmc-envelope://base-rate/{index}"
                ),
                kind=kind,
                metadata={
                    "candidate_index": index,
                    "source_label": row.get("source_label"),
                    "contract_reference": row.get("source_contract_reference"),
                    "authority_readiness": row.get("authority_readiness"),
                },
            )
            if ref and (ref.kind, ref.source_hash) not in seen:
                out.append(ref)
                seen.add((ref.kind, ref.source_hash))

    tariff = envelope.get("tariff_rule_authority") or {}
    rules = tariff.get("rules") or {}
    if isinstance(rules, Mapping):
        for rule_type, result in rules.items():
            if not isinstance(result, Mapping):
                continue
            candidates = result.get("candidates") or []
            for index, row in enumerate(candidates):
                if not isinstance(row, Mapping):
                    continue
                digest = str(row.get("source_sha256") or "")
                ref = _hash_evidence(
                    digest=digest,
                    locator=str(
                        row.get("evidence_url")
                        or row.get("final_url")
                        or row.get("evidence_locator")
                        or f"fmc-envelope://rule/{rule_type}/{index}"
                    ),
                    kind="fmc_tariff_rule_source",
                    metadata={
                        "rule_type": str(rule_type),
                        "candidate_index": index,
                        "source_version": row.get("source_version"),
                        "effective_from": row.get("effective_from"),
                        "effective_to": row.get("effective_to"),
                        "confidence": row.get("confidence"),
                    },
                )
                if ref and (ref.kind, ref.source_hash) not in seen:
                    out.append(ref)
                    seen.add((ref.kind, ref.source_hash))

    return tuple(out)


def _fmc_blockers(
    context: FreightAuthorityContext,
    finding_type: FindingType,
    normalized_category: str | None,
) -> tuple[str, ...]:
    envelope = context.fmc_envelope
    if envelope is None:
        return ()

    blockers: list[str] = []
    status = str(envelope.get("status") or "")
    if status not in {"AUTHORITY_ENVELOPE_READY", "BASE_RATE_READY_RULE_GAPS"}:
        blockers.append(f"FMC_ENVELOPE_{status or 'UNKNOWN'}")

    if context.fmc_organization_no is not None:
        if _text(str(envelope.get("fmc_organization_no") or "")) != _text(
            context.fmc_organization_no
        ):
            blockers.append("FMC_ORGANIZATION_MISMATCH")

    if _text(str(envelope.get("shipment_date") or "")) != _text(context.service_date):
        blockers.append("FMC_SERVICE_DATE_MISMATCH")

    lane = envelope.get("lane") or {}
    if _norm(str(lane.get("currency") or "")) != _norm(context.currency):
        blockers.append("FMC_CURRENCY_MISMATCH")
    if context.origin is not None and _norm(str(lane.get("origin") or "")) != _norm(context.origin):
        blockers.append("FMC_ORIGIN_MISMATCH")
    if context.destination is not None and _norm(str(lane.get("destination") or "")) != _norm(context.destination):
        blockers.append("FMC_DESTINATION_MISMATCH")
    if context.container_type is not None and _norm_container(
        str(lane.get("container_type") or "")
    ) != _norm_container(context.container_type):
        blockers.append("FMC_CONTAINER_MISMATCH")

    if envelope.get("blockers"):
        blockers.extend(
            f"FMC_{_norm(str(item)).replace(' ', '_')}"
            for item in envelope.get("blockers") or []
        )

    category = _norm(normalized_category or "")
    tariff_sensitive = category not in {"LINEHAUL", ""}
    if (
        status == "BASE_RATE_READY_RULE_GAPS"
        and (tariff_sensitive or finding_type is FindingType.TOTAL_MISMATCH)
    ):
        blockers.append("FMC_TARIFF_RULE_GAPS")

    return tuple(dict.fromkeys(blockers))


def resolve_freight_authority(
    context: FreightAuthorityContext,
    *,
    finding_type: FindingType,
    normalized_category: str | None,
) -> FreightAuthorityResolution:
    """Resolve one exact buyer/carrier/date/category authority or fail closed."""
    codes = _charge_codes(finding_type, normalized_category)
    candidates = tuple(
        sorted(
            (
                rule for rule in context.charge_rules
                if _rule_matches(rule, context, codes)
            ),
            key=lambda rule: rule.rule_hash,
        )
    )

    blockers: list[str] = list(
        _fmc_blockers(context, finding_type, normalized_category)
    )

    if not codes:
        blockers.append("NO_CHARGE_CODE_MAPPING")
    if not candidates:
        blockers.append("NO_APPLICABLE_CHARGE_RULE")
    elif len(candidates) > 1:
        blockers.append("AMBIGUOUS_APPLICABLE_CHARGE_RULE")
    elif not candidates[0].verified_controlling_authority:
        blockers.append("CHARGE_RULE_AUTHORITY_NOT_VERIFIED")

    fmc_evidence: tuple[EvidenceRef, ...] = ()
    envelope_hash: str | None = None
    if context.fmc_envelope is not None:
        envelope_payload = dict(context.fmc_envelope)
        envelope_hash = canonical_hash(envelope_payload)
        envelope_verified = not bool(blockers)
        envelope_ref = EvidenceRef(
            evidence_id=f"freight-authority-envelope:{envelope_hash}",
            source_hash=envelope_hash,
            locator="recoveryos://freight/fmc-authority-envelope",
            kind="freight_authority_envelope",
            verified=envelope_verified,
            metadata={
                "status": context.fmc_envelope.get("status"),
                "shipment_date": context.fmc_envelope.get("shipment_date"),
                "fmc_organization_no": context.fmc_envelope.get("fmc_organization_no"),
            },
        )
        fmc_evidence = (envelope_ref, *_fmc_source_evidence(context.fmc_envelope))

    matched_hashes = tuple(rule.rule_hash for rule in candidates)
    selected = candidates[0] if len(candidates) == 1 else None
    authority_rule: RuleRef | None = None

    if selected is not None and not blockers:
        authority_rule = RuleRef(
            rule_id="freight-charge-rule:" + selected.rule_hash,
            source_hash=selected.rule_hash,
            effective_from=selected.effective_from,
            effective_to=selected.effective_to,
            verified_controlling=True,
            source_locator=f"freight-authority://{selected.authority_document_id}",
            metadata={
                "source": "freight.finding_factory.ChargeRule",
                "authority_document_id": selected.authority_document_id,
                "document_source_hash": selected.document_source_hash,
                "charge_code": selected.charge_code,
                "pricing_model": selected.pricing_model,
                "fixed_cents": selected.fixed_cents,
                "unit_rate_cents": selected.unit_rate_cents,
                "rule_hash": selected.rule_hash,
                "fmc_envelope_hash": envelope_hash,
                "fmc_envelope_status": (
                    context.fmc_envelope.get("status")
                    if context.fmc_envelope is not None else None
                ),
            },
        )

    document_evidence = (
        _authority_document_evidence(selected)
        if selected is not None
        else ()
    )
    evidence = (*document_evidence, *fmc_evidence)

    body = {
        "schema": 1,
        "buyer_id": context.buyer_id,
        "business_unit": context.business_unit,
        "customer_id": context.customer_id,
        "carrier_id": context.carrier_id,
        "currency": _norm(context.currency),
        "service_date": context.service_date,
        "finding_type": finding_type.value,
        "normalized_category": normalized_category,
        "matched_rule_hashes": list(matched_hashes),
        "blockers": list(dict.fromkeys(blockers)),
        "rule_hash": authority_rule.proof_hash if authority_rule else None,
        "evidence_hashes": [item.proof_hash for item in evidence],
    }

    return FreightAuthorityResolution(
        rule=authority_rule,
        evidence=tuple(evidence),
        blockers=tuple(dict.fromkeys(blockers)),
        matched_rule_hashes=matched_hashes,
        authority_hash=canonical_hash(body),
    )


__all__ = [
    "FreightAuthorityContext",
    "FreightAuthorityResolution",
    "resolve_freight_authority",
]
