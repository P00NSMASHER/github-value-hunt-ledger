"""Deterministically freeze a pilot population from an accepted charge batch.

The builder removes one manual step from the audit path. Invoice/shipment scope
is derived from normalized charge evidence, with identity conflicts failing
closed. Multiple charge lines for one invoice/shipment collapse to one frozen
population row whose source proof binds every contributing charge row.
"""
from __future__ import annotations

from dataclasses import dataclass

from freight.contracts import PopulationManifest, PopulationRow, canonical_hash, freeze_population
from freight.invoice_csv_adapter import InvoiceChargeCSVBatch


@dataclass(frozen=True)
class PopulationBuild:
    buyer_id: str
    business_unit: str
    selection_rule: str
    invoice_count: int
    charge_count: int
    invoice_charge_adapter_hash: str
    population: PopulationManifest
    builder_hash: str


def build_population_from_charge_batch(
    batch: InvoiceChargeCSVBatch,
    *,
    selection_rule: str,
) -> PopulationBuild:
    if not isinstance(selection_rule, str) or not selection_rule.strip():
        raise ValueError("selection_rule is required")
    selection_rule = selection_rule.strip()

    grouped: dict[tuple[str, str], dict] = {}
    for charge in batch.charges:
        if (charge.buyer_id, charge.business_unit) != (batch.buyer_id, batch.business_unit):
            raise ValueError("charge scope does not match invoice batch")
        key = (charge.invoice_id, charge.shipment_id)
        identity = (charge.customer_id, charge.carrier_id, charge.currency)
        current = grouped.get(key)
        if current is None:
            grouped[key] = {
                "invoice_id": charge.invoice_id,
                "shipment_id": charge.shipment_id,
                "customer_id": charge.customer_id,
                "carrier_id": charge.carrier_id,
                "currency": charge.currency,
                "identity": identity,
                "charge_source_hashes": [charge.source_hash],
            }
            continue
        if current["identity"] != identity:
            raise ValueError(
                "invoice/shipment identity conflict: customer/carrier/currency changed for "
                + repr(key)
            )
        current["charge_source_hashes"].append(charge.source_hash)

    rows = []
    for key in sorted(grouped):
        item = grouped[key]
        source_hash = canonical_hash({
            "schema": 1,
            "invoice_charge_adapter_hash": batch.adapter_hash,
            "invoice_id": item["invoice_id"],
            "shipment_id": item["shipment_id"],
            "customer_id": item["customer_id"],
            "carrier_id": item["carrier_id"],
            "currency": item["currency"],
            "charge_source_hashes": sorted(item["charge_source_hashes"]),
        })
        rows.append(PopulationRow(
            invoice_id=item["invoice_id"],
            shipment_id=item["shipment_id"],
            customer_id=item["customer_id"],
            carrier_id=item["carrier_id"],
            currency=item["currency"],
            source_hash=source_hash,
        ))

    population = freeze_population(
        batch.buyer_id,
        batch.business_unit,
        selection_rule,
        rows,
    )
    body = {
        "schema": 1,
        "buyer_id": batch.buyer_id,
        "business_unit": batch.business_unit,
        "selection_rule": selection_rule,
        "invoice_charge_adapter_hash": batch.adapter_hash,
        "file_sha256": batch.file_sha256,
        "charge_count": len(batch.charges),
        "invoice_count": len(rows),
        "population_hash": population.manifest_hash,
    }
    return PopulationBuild(
        buyer_id=batch.buyer_id,
        business_unit=batch.business_unit,
        selection_rule=selection_rule,
        invoice_count=len(rows),
        charge_count=len(batch.charges),
        invoice_charge_adapter_hash=batch.adapter_hash,
        population=population,
        builder_hash=canonical_hash(body),
    )
