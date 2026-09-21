import pytest

from freight.invoice_csv_adapter import parse_invoice_charge_csv


HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"


def csv_bytes(rows: str, *, bom: bool = False) -> bytes:
    data = (HEADER + rows).encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def test_valid_csv_is_scoped_by_caller_and_normalized():
    batch = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("INV-1,SHP-1,CUST-1,CAR-1,usd,CH-1,detention,2026-09-10,2,12500\n"),
        buyer_id=" buyer ",
        business_unit=" ops ",
    )
    charge = batch.charges[0]
    assert charge.buyer_id == "buyer"
    assert charge.business_unit == "ops"
    assert charge.currency == "USD"
    assert charge.charge_code == "DETENTION"
    assert charge.quantity_units == 2
    assert charge.billed_cents == 12500
    assert len(charge.source_hash) == 64
    assert len(batch.file_sha256) == 64
    assert len(batch.adapter_hash) == 64


def test_utf8_bom_is_accepted_and_deterministic():
    plain = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10,1,100\n"),
        buyer_id="b", business_unit="u",
    )
    bom = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10,1,100\n", bom=True),
        buyer_id="b", business_unit="u",
    )
    assert plain.charges[0].invoice_id == bom.charges[0].invoice_id
    assert plain.file_sha256 != bom.file_sha256
    assert plain.adapter_hash != bom.adapter_hash


def test_file_change_changes_row_proof_and_adapter_hash():
    a = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10,1,100\n"),
        buyer_id="b", business_unit="u",
    )
    b = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10,1,101\n"),
        buyer_id="b", business_unit="u",
    )
    assert a.charges[0].source_hash != b.charges[0].source_hash
    assert a.adapter_hash != b.adapter_hash


@pytest.mark.parametrize("bad", ["10.0", "1,000", "+10", "-1"])
def test_billed_cents_must_be_exact_unsigned_integer_text(bad):
    quoted = f'"{bad}"' if "," in bad else bad
    with pytest.raises(ValueError, match="billed_cents"):
        parse_invoice_charge_csv(
            filename="charges.csv",
            data=csv_bytes(f"I,S,C,K,USD,X,FUEL,2026-09-10,1,{quoted}\n"),
            buyer_id="b", business_unit="u",
        )


def test_quantity_must_be_positive_integer():
    with pytest.raises(ValueError, match="quantity_units"):
        parse_invoice_charge_csv(
            filename="charges.csv",
            data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10,0,100\n"),
            buyer_id="b", business_unit="u",
        )


def test_duplicate_charge_id_fails_closed():
    rows = (
        "I1,S1,C,K,USD,X,FUEL,2026-09-10,1,100\n"
        "I2,S2,C,K,USD,X,FUEL,2026-09-10,1,200\n"
    )
    with pytest.raises(ValueError, match="duplicate charge_id"):
        parse_invoice_charge_csv(
            filename="charges.csv", data=csv_bytes(rows),
            buyer_id="b", business_unit="u",
        )


def test_schema_mismatch_rejects_injected_scope_column():
    data = (
        "buyer_id," + HEADER
        + "evil,I,S,C,K,USD,X,FUEL,2026-09-10,1,100\n"
    ).encode()
    with pytest.raises(ValueError, match="schema mismatch"):
        parse_invoice_charge_csv(
            filename="charges.csv", data=data,
            buyer_id="real-buyer", business_unit="real-unit",
        )


def test_non_csv_and_malformed_dates_fail_closed():
    with pytest.raises(ValueError):
        parse_invoice_charge_csv(
            filename="charges.txt",
            data=b"hello",
            buyer_id="b", business_unit="u",
        )
    with pytest.raises(ValueError, match="service_date"):
        parse_invoice_charge_csv(
            filename="charges.csv",
            data=csv_bytes("I,S,C,K,USD,X,FUEL,09/10/2026,1,100\n"),
            buyer_id="b", business_unit="u",
        )


def test_header_order_may_vary_but_header_set_must_be_exact():
    data = (
        "charge_id,invoice_id,shipment_id,customer_id,carrier_id,currency,charge_code,service_date,quantity_units,billed_cents\n"
        "X,I,S,C,K,USD,FUEL,2026-09-10,1,100\n"
    ).encode()
    batch = parse_invoice_charge_csv(
        filename="charges.csv", data=data,
        buyer_id="b", business_unit="u",
    )
    assert batch.charges[0].charge_id == "X"


def test_numeric_fields_trim_surrounding_export_whitespace():
    batch = parse_invoice_charge_csv(
        filename="charges.csv",
        data=csv_bytes("I,S,C,K,USD,X,FUEL,2026-09-10, 1 , 100 \n"),
        buyer_id="b", business_unit="u",
    )
    assert batch.charges[0].quantity_units == 1
    assert batch.charges[0].billed_cents == 100
