import pytest

from freight.finding_factory import FIXED, INCLUDED, PER_UNIT
from freight.rule_csv_adapter import parse_charge_rule_csv


HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
DOC_HASH = "a" * 64


def data(rows: str) -> bytes:
    return (HEADER + rows).encode("utf-8")


def parse(rows: str, **overrides):
    kwargs = dict(
        filename="rules.csv",
        data=data(rows),
        buyer_id="buyer",
        business_unit="unit",
        customer_id="customer",
        carrier_id="carrier",
        currency="usd",
        authority_document_id="rate-confirmation-1",
        source_document_sha256=DOC_HASH,
        verified_controlling_authority=True,
    )
    kwargs.update(overrides)
    return parse_charge_rule_csv(**kwargs)


def test_fixed_included_and_per_unit_rows_are_normalized():
    batch = parse(
        "DETENTION,FIXED,2026-09-01,2026-09-30,10000,\n"
        "FUEL,INCLUDED,2026-09-01,,,\n"
        "PALLET,PER_UNIT,2026-09-01,,,500\n"
    )
    assert [r.pricing_model for r in batch.rules] == [FIXED, INCLUDED, PER_UNIT]
    assert batch.rules[0].fixed_cents == 10000
    assert batch.rules[1].fixed_cents is None and batch.rules[1].unit_rate_cents is None
    assert batch.rules[2].unit_rate_cents == 500
    assert all(r.currency == "USD" for r in batch.rules)
    assert all(r.verified_controlling_authority is True for r in batch.rules)
    assert all(r.document_source_hash == DOC_HASH for r in batch.rules)
    assert len(batch.adapter_hash) == 64


def test_csv_cannot_self_assert_scope_or_authority_verification():
    raw = (
        "verified_controlling_authority," + HEADER
        + "true,DETENTION,FIXED,2026-09-01,,10000,\n"
    ).encode()
    with pytest.raises(ValueError, match="schema mismatch"):
        parse_charge_rule_csv(
            filename="rules.csv", data=raw,
            buyer_id="real", business_unit="unit", customer_id="customer",
            carrier_id="carrier", currency="USD",
            authority_document_id="doc", source_document_sha256=DOC_HASH,
            verified_controlling_authority=False,
        )


def test_unverified_trusted_context_produces_unverified_rules():
    batch = parse(
        "DETENTION,FIXED,2026-09-01,,10000,\n",
        verified_controlling_authority=False,
    )
    assert batch.rules[0].verified_controlling_authority is False


@pytest.mark.parametrize("flag", [1, 0, "true", None])
def test_verification_state_must_be_actual_boolean(flag):
    with pytest.raises(ValueError, match="boolean"):
        parse(
            "DETENTION,FIXED,2026-09-01,,10000,\n",
            verified_controlling_authority=flag,
        )


@pytest.mark.parametrize("bad", ["10.5", "+10", "-1", "1,000"])
def test_rule_money_requires_exact_unsigned_integer_or_blank(bad):
    quoted = f'"{bad}"' if "," in bad else bad
    with pytest.raises(ValueError, match="fixed_cents"):
        parse(f"DETENTION,FIXED,2026-09-01,,{quoted},\n")


def test_pricing_model_column_semantics_fail_closed():
    with pytest.raises(ValueError, match="INCLUDED"):
        parse("FUEL,INCLUDED,2026-09-01,,1,\n")
    with pytest.raises(ValueError, match="FIXED"):
        parse("DETENTION,FIXED,2026-09-01,,,\n")
    with pytest.raises(ValueError, match="PER_UNIT"):
        parse("PALLET,PER_UNIT,2026-09-01,,100,500\n")
    with pytest.raises(ValueError, match="unsupported"):
        parse("X,PERCENT,2026-09-01,,100,\n")


def test_effective_date_range_is_validated():
    with pytest.raises(ValueError, match="effective_to cannot precede"):
        parse("DETENTION,FIXED,2026-09-10,2026-09-01,10000,\n")


def test_duplicate_normalized_rule_is_rejected():
    row = "DETENTION,FIXED,2026-09-01,,10000,\n"
    with pytest.raises(ValueError, match="duplicate normalized rule"):
        parse(row + row)


def test_semantic_change_changes_rule_and_adapter_proof():
    a = parse("DETENTION,FIXED,2026-09-01,,10000,\n")
    b = parse("DETENTION,FIXED,2026-09-01,,10001,\n")
    assert a.rules[0].rule_hash != b.rules[0].rule_hash
    assert a.adapter_hash != b.adapter_hash


def test_source_document_hash_is_trusted_required_provenance():
    with pytest.raises(ValueError, match="SHA-256"):
        parse(
            "DETENTION,FIXED,2026-09-01,,10000,\n",
            source_document_sha256="not-a-hash",
        )


def test_blank_effective_to_is_open_ended():
    batch = parse("DETENTION,FIXED,2026-09-01,,10000,\n")
    assert batch.rules[0].effective_to is None
