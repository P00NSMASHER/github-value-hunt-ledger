"""Raw multi-branch Recovery Scan 360 ingestion.

This module converts explicit structured domain records into the deterministic
branch engines, freezes every load-bearing source into a scan manifest, and then
runs the common RecoveryOS proof/ledger pipeline.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from freight.finding_factory import ChargeRule, InvoiceCharge, derive_charge

from .branches.freight import from_freight_derivation
from .engine import RecoveryEngine, RecoveryObservation
from .engines.ap import APInvoice, APPayment, detect_ap_overpayments
from .engines.construction import (
    ConstructionEntitlement,
    ScheduleImpact,
    detect_construction_recovery,
)
from .engines.duty import DutyRate, ImportEntryLine, detect_duty_overpayments
from .engines.payer import FeeScheduleRate, PayerServiceLine, detect_payer_underpayments
from .engines.utility import bill, detect_utility_variance, tariff, tier
from .ledger import RecoveryLedger
from .models import Branch, EvidenceRef, RuleRef, canonical_hash
from .packets import build_client_portfolio_packet, build_recovery_packet, submission_ready
from .scan import SourceManifestEntry, freeze_scan, run_scan


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _items(value: Any, name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if type(value) is not bool:
        raise ValueError("boolean field must be true or false")
    return value


def _source(
    branch: Branch,
    source_hash: str,
    locator: str,
    kind: str,
) -> SourceManifestEntry:
    identity = {
        "branch": branch.value,
        "source_hash": source_hash,
        "locator": locator,
        "kind": kind,
    }
    return SourceManifestEntry(
        source_id=f"raw:{branch.value}:" + canonical_hash(identity)[:24],
        branch=branch,
        source_hash=source_hash,
        locator=locator,
        kind=kind,
    )


def _rule(value: Any) -> RuleRef:
    item = _mapping(value, "rule")
    return RuleRef(
        rule_id=item["rule_id"],
        source_hash=item["source_hash"],
        effective_from=item["effective_from"],
        effective_to=item.get("effective_to"),
        verified_controlling=_bool(item.get("verified_controlling"), False),
        source_locator=item["source_locator"],
        jurisdiction=item.get("jurisdiction"),
        metadata=item.get("metadata", {}),
    )


def _evidence(values: Any) -> tuple[EvidenceRef, ...]:
    raw = _items(values, "evidence")
    if not raw:
        raise ValueError("evidence cannot be empty")
    return tuple(
        EvidenceRef(
            evidence_id=item["evidence_id"],
            source_hash=item["source_hash"],
            locator=item["locator"],
            kind=item["kind"],
            verified=_bool(item.get("verified"), False),
            metadata=item.get("metadata", {}),
        )
        for value in raw
        for item in (_mapping(value, "evidence item"),)
    )


class RawScanBuilder:
    def __init__(self, client_id: str) -> None:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_id is required")
        self.client_id = client_id.strip()
        self.observations: list[RecoveryObservation] = []
        self.sources: dict[str, SourceManifestEntry] = {}
        self.branches: set[Branch] = set()

    def add_source(self, branch: Branch, source_hash: str, locator: str, kind: str) -> None:
        source = _source(branch, source_hash, locator, kind)
        existing = self.sources.get(source.source_id)
        if existing is not None and existing != source:
            raise ValueError("source manifest identity collision")
        self.sources[source.source_id] = source
        self.branches.add(branch)

    def add_observations(self, observations: tuple[RecoveryObservation, ...] | list[RecoveryObservation]) -> None:
        self.observations.extend(observations)
        self.branches.update(item.branch for item in observations)


def _parse_ap(builder: RawScanBuilder, value: Any) -> None:
    if value is None:
        return
    root = _mapping(value, "ap")
    invoices = []
    for raw in _items(root.get("invoices"), "ap.invoices"):
        item = _mapping(raw, "AP invoice")
        invoice = APInvoice(
            vendor_id=item["vendor_id"],
            invoice_id=item["invoice_id"],
            invoice_date=item["invoice_date"],
            amount_cents=item["amount_cents"],
            currency=item.get("currency", "USD"),
            source_hash=item["source_hash"],
            locator=item["locator"],
            verified=_bool(item.get("verified"), False),
        )
        invoices.append(invoice)
        builder.add_source(Branch.AP, invoice.source_hash, invoice.locator, "ap_invoice")

    payments = []
    for raw in _items(root.get("payments"), "ap.payments"):
        item = _mapping(raw, "AP payment")
        payment = APPayment(
            vendor_id=item["vendor_id"],
            invoice_id=item["invoice_id"],
            payment_id=item["payment_id"],
            payment_date=item["payment_date"],
            amount_cents=item["amount_cents"],
            currency=item.get("currency", "USD"),
            source_hash=item["source_hash"],
            locator=item["locator"],
            verified=_bool(item.get("verified"), False),
            posted=_bool(item.get("posted"), True),
        )
        payments.append(payment)
        builder.add_source(Branch.AP, payment.source_hash, payment.locator, "ap_payment")

    builder.add_observations(list(detect_ap_overpayments(
        client_id=builder.client_id,
        invoices=invoices,
        payments=payments,
    )))


def _parse_utility(builder: RawScanBuilder, value: Any) -> None:
    for raw_account in _items(value, "utility"):
        account = _mapping(raw_account, "utility account")
        utility_id = account["utility_id"]
        t = _mapping(account["tariff"], "utility tariff")
        tiers = tuple(
            tier(item.get("up_to_kwh"), item["rate_cents_per_kwh"])
            for raw_tier in _items(t.get("energy_tiers"), "utility tariff energy_tiers")
            for item in (_mapping(raw_tier, "energy tier"),)
        )
        tariff_obj = tariff(
            tariff_id=t["tariff_id"],
            effective_from=t["effective_from"],
            effective_to=t.get("effective_to"),
            fixed_charge_cents=t["fixed_charge_cents"],
            energy_tiers=tiers,
            demand_rate_cents_per_kw=t.get("demand_rate_cents_per_kw", "0"),
            source_hash=t["source_hash"],
            locator=t["locator"],
            verified=_bool(t.get("verified"), False),
            jurisdiction=t.get("jurisdiction"),
        )
        builder.add_source(
            Branch.UTILITY, tariff_obj.source_hash, tariff_obj.locator, "utility_tariff"
        )

        for raw_bill in _items(account.get("bills"), "utility bills"):
            item = _mapping(raw_bill, "utility bill")
            bill_obj = bill(
                bill_id=item["bill_id"],
                bill_date=item["bill_date"],
                usage_kwh=item.get("usage_kwh", "0"),
                demand_kw=item.get("demand_kw", "0"),
                billed_cents=item["billed_cents"],
                currency=item.get("currency", "USD"),
                source_hash=item["source_hash"],
                locator=item["locator"],
                verified=_bool(item.get("verified"), False),
            )
            builder.add_source(
                Branch.UTILITY, bill_obj.source_hash, bill_obj.locator, "utility_bill"
            )
            builder.add_observations([detect_utility_variance(
                client_id=builder.client_id,
                utility_id=utility_id,
                tariff=tariff_obj,
                bill=bill_obj,
            )])


def _parse_payer(builder: RawScanBuilder, value: Any) -> None:
    for raw_payer in _items(value, "payer"):
        root = _mapping(raw_payer, "payer block")
        payer_id = root["payer_id"]
        rates = []
        for raw_rate in _items(root.get("rates"), "payer rates"):
            item = _mapping(raw_rate, "payer rate")
            rate = FeeScheduleRate(
                payer_id=payer_id,
                rate_id=item["rate_id"],
                procedure_code=item["procedure_code"],
                effective_from=item["effective_from"],
                effective_to=item.get("effective_to"),
                allowed_cents_per_unit=item["allowed_cents_per_unit"],
                source_hash=item["source_hash"],
                locator=item["locator"],
                verified=_bool(item.get("verified"), False),
            )
            rates.append(rate)
            builder.add_source(
                Branch.PAYER, rate.source_hash, rate.locator, "payer_fee_schedule"
            )

        lines = []
        for raw_line in _items(root.get("service_lines"), "payer service_lines"):
            item = _mapping(raw_line, "payer service line")
            line = PayerServiceLine(
                claim_id=item["claim_id"],
                service_line_id=item["service_line_id"],
                service_date=item["service_date"],
                procedure_code=item["procedure_code"],
                units=item.get("units", 1),
                paid_cents=item["paid_cents"],
                currency=item.get("currency", "USD"),
                source_hash=item["source_hash"],
                locator=item["locator"],
                verified=_bool(item.get("verified"), False),
            )
            lines.append(line)
            builder.add_source(
                Branch.PAYER, line.source_hash, line.locator, "payer_service_line"
            )

        builder.add_observations(list(detect_payer_underpayments(
            client_id=builder.client_id,
            payer_id=payer_id,
            rates=rates,
            service_lines=lines,
        )))


def _parse_duty(builder: RawScanBuilder, value: Any) -> None:
    if value is None:
        return
    root = _mapping(value, "duty")
    counterparty = root["customs_counterparty_id"]
    rates = []
    for raw_rate in _items(root.get("rates"), "duty rates"):
        item = _mapping(raw_rate, "duty rate")
        rate = DutyRate(
            rate_id=item["rate_id"],
            hts_code=item["hts_code"],
            effective_from=item["effective_from"],
            effective_to=item.get("effective_to"),
            ad_valorem_bps=item.get("ad_valorem_bps", 0),
            specific_cents_per_unit=Decimal(str(item.get("specific_cents_per_unit", "0"))),
            source_hash=item["source_hash"],
            locator=item["locator"],
            verified=_bool(item.get("verified"), False),
            jurisdiction=item.get("jurisdiction", "US"),
        )
        rates.append(rate)
        builder.add_source(Branch.DUTY, rate.source_hash, rate.locator, "hts_tariff_rule")

    lines = []
    for raw_line in _items(root.get("lines"), "duty lines"):
        item = _mapping(raw_line, "import entry line")
        line = ImportEntryLine(
            entry_id=item["entry_id"],
            line_id=item["line_id"],
            entry_date=item["entry_date"],
            hts_code=item["hts_code"],
            customs_value_cents=item["customs_value_cents"],
            quantity=Decimal(str(item.get("quantity", "0"))),
            paid_duty_cents=item["paid_duty_cents"],
            currency=item.get("currency", "USD"),
            source_hash=item["source_hash"],
            locator=item["locator"],
            verified=_bool(item.get("verified"), False),
        )
        lines.append(line)
        builder.add_source(Branch.DUTY, line.source_hash, line.locator, "customs_entry_line")

    builder.add_observations(list(detect_duty_overpayments(
        client_id=builder.client_id,
        customs_counterparty_id=counterparty,
        rates=rates,
        lines=lines,
    )))


def _parse_construction(builder: RawScanBuilder, value: Any) -> None:
    for raw_case in _items(value, "construction"):
        root = _mapping(raw_case, "construction case")
        entitlement_raw = _mapping(root["entitlement"], "construction entitlement")
        rule_obj = _rule(entitlement_raw["rule"])
        evidence = _evidence(entitlement_raw["evidence"])
        entitlement = ConstructionEntitlement(
            event_id=entitlement_raw["event_id"],
            event_date=entitlement_raw["event_date"],
            entitled_cents=entitlement_raw["entitled_cents"],
            paid_cents=entitlement_raw["paid_cents"],
            currency=entitlement_raw.get("currency", "USD"),
            rule=rule_obj,
            evidence=evidence,
            entitlement_type=entitlement_raw.get("entitlement_type", "change"),
        )
        builder.add_source(
            Branch.CONSTRUCTION, rule_obj.source_hash, rule_obj.source_locator, "construction_rule"
        )
        for ref in evidence:
            builder.add_source(Branch.CONSTRUCTION, ref.source_hash, ref.locator, ref.kind)

        impact_raw = root.get("schedule_impact")
        impact = None
        if impact_raw is not None:
            item = _mapping(impact_raw, "schedule impact")
            impact = ScheduleImpact(
                analysis_id=item["analysis_id"],
                method=item["method"],
                impact_days=item["impact_days"],
                analysis_hash=item["analysis_hash"],
                locator=item["locator"],
                baseline_hash=item["baseline_hash"],
                comparison_hash=item["comparison_hash"],
                verified=_bool(item.get("verified"), False),
            )
            builder.add_source(
                Branch.CONSTRUCTION,
                impact.analysis_hash,
                impact.locator,
                "forensic_schedule_impact",
            )

        require_impact = _bool(root.get("require_schedule_impact"), False)
        if require_impact and impact is None:
            missing_hash = canonical_hash({
                "schema": 1,
                "event_id": entitlement.event_id,
                "missing": "forensic_schedule_impact",
            })
            builder.add_source(
                Branch.CONSTRUCTION,
                missing_hash,
                "recoveryworks://missing/forensic-schedule-impact",
                "required_schedule_impact",
            )

        builder.add_observations([detect_construction_recovery(
            client_id=builder.client_id,
            counterparty_id=root["counterparty_id"],
            entitlement=entitlement,
            schedule_impact=impact,
            require_schedule_impact=require_impact,
        )])


def _parse_freight(builder: RawScanBuilder, value: Any) -> None:
    if value is None:
        return
    root = _mapping(value, "freight")
    rules = []
    for raw_rule in _items(root.get("rules"), "freight rules"):
        item = _mapping(raw_rule, "freight rule")
        rule = ChargeRule(
            buyer_id=builder.client_id,
            business_unit=item["business_unit"],
            customer_id=item["customer_id"],
            carrier_id=item["carrier_id"],
            currency=item.get("currency", "USD"),
            authority_document_id=item["authority_document_id"],
            charge_code=item["charge_code"],
            pricing_model=item["pricing_model"],
            effective_from=item["effective_from"],
            effective_to=item.get("effective_to"),
            document_source_hash=item["document_source_hash"],
            verified_controlling_authority=_bool(
                item.get("verified_controlling_authority"), False
            ),
            fixed_cents=item.get("fixed_cents"),
            unit_rate_cents=item.get("unit_rate_cents"),
        )
        rules.append(rule)
        builder.add_source(
            Branch.FREIGHT,
            rule.document_source_hash,
            f"freight://authority/{rule.authority_document_id}",
            "freight_charge_rule",
        )

    for raw_charge in _items(root.get("charges"), "freight charges"):
        item = _mapping(raw_charge, "freight charge")
        charge = InvoiceCharge(
            buyer_id=builder.client_id,
            business_unit=item["business_unit"],
            invoice_id=item["invoice_id"],
            shipment_id=item["shipment_id"],
            customer_id=item["customer_id"],
            carrier_id=item["carrier_id"],
            currency=item.get("currency", "USD"),
            charge_id=item["charge_id"],
            charge_code=item["charge_code"],
            service_date=item["service_date"],
            quantity_units=item.get("quantity_units", 1),
            billed_cents=item["billed_cents"],
            source_hash=item["source_hash"],
        )
        builder.add_source(
            Branch.FREIGHT,
            charge.source_hash,
            f"freight://charge/{charge.charge_id}",
            "freight_invoice_charge",
        )
        derivation = derive_charge(charge, rules)
        matched_rules = [
            candidate
            for candidate in rules
            if candidate.rule_hash in derivation.matched_rule_hashes
        ]
        if derivation.finding is None or len(matched_rules) != 1:
            continue
        matched_rule = matched_rules[0]
        builder.add_source(
            Branch.FREIGHT,
            derivation.derivation_hash,
            f"freight://derivation/{charge.charge_id}",
            "freight_charge_derivation",
        )
        builder.add_observations([
            from_freight_derivation(derivation, charge, matched_rule)
        ])


def build_raw_scan(payload: Any):
    root = _mapping(payload, "raw scan payload")
    if root.get("schema") != 1:
        raise ValueError("unsupported raw scan schema")
    builder = RawScanBuilder(root["client_id"])

    _parse_ap(builder, root.get("ap"))
    _parse_utility(builder, root.get("utility"))
    _parse_payer(builder, root.get("payer"))
    _parse_duty(builder, root.get("duty"))
    _parse_construction(builder, root.get("construction"))
    _parse_freight(builder, root.get("freight"))

    if not builder.branches:
        raise ValueError("raw scan must include at least one recovery branch")

    manifest = freeze_scan(
        scan_id=root["scan_id"],
        client_id=builder.client_id,
        branches=builder.branches,
        selection_rule=root["selection_rule"],
        sources=builder.sources.values(),
    )
    return manifest, tuple(builder.observations)


def execute_raw_scan_payload(payload: Any) -> tuple[dict[str, Any], RecoveryLedger]:
    manifest, observations = build_raw_scan(payload)
    batch = run_scan(manifest, observations, engine=RecoveryEngine())
    ledger = RecoveryLedger()
    records = tuple(ledger.add(finding) for finding in batch.findings)
    packets = tuple(build_recovery_packet(record) for record in records)
    portfolio = build_client_portfolio_packet(ledger, manifest.client_id)
    result = {
        "schema": 1,
        "input_mode": "raw",
        "scan_id": manifest.scan_id,
        "client_id": manifest.client_id,
        "branches": [branch.value for branch in manifest.branches],
        "source_count": len(manifest.sources),
        "observation_count": len(observations),
        "manifest_hash": manifest.manifest_hash,
        "batch_hash": batch.batch_hash,
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "audit_head": ledger.audit_head,
        "portfolio": portfolio,
        "findings": [{
            "finding_id": packet.finding_id,
            "branch": packet.branch,
            "reference": packet.reference,
            "case_state": packet.case_state,
            "potential_recovery_cents": packet.potential_recovery_cents,
            "packet_hash": packet.packet_hash,
            "submission_ready": submission_ready(packet),
        } for packet in packets],
    }
    return result, ledger


def run_raw_scan_payload(payload: Any) -> dict[str, Any]:
    result, _ = execute_raw_scan_payload(payload)
    return result
