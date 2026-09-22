from dataclasses import replace

import pytest

from freight.invoice_csv_adapter import parse_invoice_charge_csv
from freight.population_builder import build_population_from_charge_batch


HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"


def batch(rows: str):
    return parse_invoice_charge_csv(
        filename="charges.csv",
        data=(HEADER + rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
    )


def test_multiple_charge_lines_collapse_to_one_population_row():
    b = batch(
        "I1,S1,C1,K1,USD,C1A,FUEL,2026-09-01,1,100\n"
        "I1,S1,C1,K1,USD,C1B,DETENTION,2026-09-01,1,200\n"
        "I2,S2,C1,K1,USD,C2A,FUEL,2026-09-01,1,300\n"
    )
    out = build_population_from_charge_batch(b, selection_rule="all September rows")
    assert out.charge_count == 3
    assert out.invoice_count == 2
    assert [row.row_key for row in out.population.rows] == ["I1|S1", "I2|S2"]
    assert all(len(row.source_hash) == 64 for row in out.population.rows)
    assert len(out.builder_hash) == 64


def test_identity_conflict_within_same_invoice_shipment_fails_closed():
    b = batch(
        "I1,S1,C1,K1,USD,C1A,FUEL,2026-09-01,1,100\n"
        "I1,S1,C2,K1,USD,C1B,DETENTION,2026-09-01,1,200\n"
    )
    with pytest.raises(ValueError, match="identity conflict"):
        build_population_from_charge_batch(b, selection_rule="period")


def test_builder_is_deterministic_for_same_accepted_batch():
    b = batch(
        "I2,S2,C,K,USD,X2,FUEL,2026-09-01,1,200\n"
        "I1,S1,C,K,USD,X1,FUEL,2026-09-01,1,100\n"
    )
    a = build_population_from_charge_batch(b, selection_rule="period")
    c = build_population_from_charge_batch(b, selection_rule="period")
    assert a == c
    assert [row.row_key for row in a.population.rows] == ["I1|S1", "I2|S2"]


def test_source_change_changes_population_and_builder_proof():
    a = build_population_from_charge_batch(
        batch("I1,S1,C,K,USD,X,FUEL,2026-09-01,1,100\n"),
        selection_rule="period",
    )
    b = build_population_from_charge_batch(
        batch("I1,S1,C,K,USD,X,FUEL,2026-09-01,1,101\n"),
        selection_rule="period",
    )
    assert a.population.manifest_hash != b.population.manifest_hash
    assert a.builder_hash != b.builder_hash


def test_selection_rule_is_part_of_frozen_population_proof():
    b = batch("I1,S1,C,K,USD,X,FUEL,2026-09-01,1,100\n")
    a = build_population_from_charge_batch(b, selection_rule="rule A")
    c = build_population_from_charge_batch(b, selection_rule="rule B")
    assert a.population.manifest_hash != c.population.manifest_hash
    assert a.builder_hash != c.builder_hash


def test_tampered_charge_scope_cannot_enter_population():
    b = batch("I1,S1,C,K,USD,X,FUEL,2026-09-01,1,100\n")
    bad_charge = replace(b.charges[0], buyer_id="other")
    tampered = replace(b, charges=(bad_charge,))
    with pytest.raises(ValueError, match="scope"):
        build_population_from_charge_batch(tampered, selection_rule="period")


def test_population_builder_does_not_collapse_delimiter_colliding_pairs():
    b = batch(
        "INV|PART,SHIP,C,K,USD,X1,FUEL,2026-09-01,1,100\n"
        "INV,PART|SHIP,C,K,USD,X2,FUEL,2026-09-01,1,200\n"
    )
    out = build_population_from_charge_batch(b, selection_rule="period")
    assert out.invoice_count == 2
    assert {row.identity_key for row in out.population.rows} == {
        ("INV|PART", "SHIP"),
        ("INV", "PART|SHIP"),
    }
