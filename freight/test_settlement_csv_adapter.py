import pytest

from freight.settlement_csv_adapter import (
    parse_counter_event_csv,
    parse_settlement_event_csv,
)


SETTLEMENT_HEADER = "event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_kind\n"
COUNTER_HEADER = "counter_id,original_event_id,currency,amount_cents,observed_at,source_kind\n"


def settlement(rows: str, **kwargs):
    args = dict(
        filename="settlements.csv",
        data=(SETTLEMENT_HEADER + rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
    )
    args.update(kwargs)
    return parse_settlement_event_csv(**args)


def counter(rows: str, **kwargs):
    args = dict(
        filename="returns.csv",
        data=(COUNTER_HEADER + rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
    )
    args.update(kwargs)
    return parse_counter_event_csv(**args)


def test_settlement_rows_are_normalized_and_scope_bound():
    batch = settlement(
        "E1,INV-1,CARRIER,CUSTOMER,usd,2500,2026-09-21T06:00:00-04:00,credit-memo\n"
    )
    event = batch.events[0]
    assert batch.buyer_id == "buyer"
    assert batch.business_unit == "unit"
    assert event.currency == "USD"
    assert event.booked_at == "2026-09-21T10:00:00.000000Z"
    assert event.source_kind == "CREDIT-MEMO"
    assert len(event.source_hash) == 64
    assert len(batch.adapter_hash) == 64


def test_counter_rows_are_normalized_and_scope_bound():
    batch = counter(
        "R1,E1,usd,500,2026-09-22T06:00:00-04:00,bank-return\n"
    )
    event = batch.events[0]
    assert event.currency == "USD"
    assert event.observed_at == "2026-09-22T10:00:00.000000Z"
    assert event.source_kind == "BANK-RETURN"
    assert len(event.source_hash) == 64


@pytest.mark.parametrize("bad", ["0", "-1", "10.5", "+10", "1,000"])
def test_settlement_money_requires_exact_positive_integer_cents(bad):
    quoted = f'"{bad}"' if "," in bad else bad
    with pytest.raises(ValueError, match="amount_cents"):
        settlement(
            f"E1,INV-1,CARRIER,CUSTOMER,USD,{quoted},2026-09-21T10:00:00Z,CREDIT\n"
        )


def test_timezone_naive_event_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        settlement(
            "E1,INV-1,CARRIER,CUSTOMER,USD,100,2026-09-21T10:00:00,CREDIT\n"
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        counter("R1,E1,USD,100,2026-09-22T10:00:00,RETURN\n")


def test_duplicate_event_identifiers_fail_closed():
    rows = (
        "E1,I1,C,B,USD,100,2026-09-21T10:00:00Z,CREDIT\n"
        "E1,I2,C,B,USD,200,2026-09-21T11:00:00Z,CREDIT\n"
    )
    with pytest.raises(ValueError, match="duplicate event_id"):
        settlement(rows)

    rows = (
        "R1,E1,USD,100,2026-09-22T10:00:00Z,RETURN\n"
        "R1,E2,USD,100,2026-09-22T11:00:00Z,RETURN\n"
    )
    with pytest.raises(ValueError, match="duplicate counter_id"):
        counter(rows)


def test_csv_cannot_self_assert_buyer_scope():
    raw = (
        "buyer_id," + SETTLEMENT_HEADER
        + "evil,E1,I1,C,B,USD,100,2026-09-21T10:00:00Z,CREDIT\n"
    ).encode()
    with pytest.raises(ValueError, match="schema mismatch"):
        parse_settlement_event_csv(
            filename="settlements.csv",
            data=raw,
            buyer_id="real",
            business_unit="unit",
        )


def test_file_or_scope_change_changes_event_proof():
    a = settlement("E1,I1,C,B,USD,100,2026-09-21T10:00:00Z,CREDIT\n")
    b = settlement("E1,I1,C,B,USD,101,2026-09-21T10:00:00Z,CREDIT\n")
    c = settlement(
        "E1,I1,C,B,USD,100,2026-09-21T10:00:00Z,CREDIT\n",
        buyer_id="other",
    )
    assert a.events[0].source_hash != b.events[0].source_hash
    assert a.events[0].source_hash != c.events[0].source_hash
    assert a.adapter_hash != b.adapter_hash


def test_invalid_currency_and_empty_files_fail_closed():
    with pytest.raises(ValueError, match="three-letter"):
        settlement("E1,I1,C,B,US,100,2026-09-21T10:00:00Z,CREDIT\n")
    with pytest.raises(ValueError, match="at least one settlement"):
        settlement("")
    with pytest.raises(ValueError, match="at least one counter"):
        counter("")
