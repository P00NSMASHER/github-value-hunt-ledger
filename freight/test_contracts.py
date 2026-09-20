from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    RecoveryLedger,
    SettlementEvent,
    REVIEW,
    VALIDATED,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
)


def row(invoice, shipment, customer="cust-1", carrier="car-1", currency="USD", source="src"):
    return PopulationRow(invoice, shipment, customer, carrier, currency, f"{source}-{invoice}-{shipment}")


def authority(authority_id="auth-1", customer="cust-1", carrier="car-1", currency="USD"):
    return AuthorityRef(authority_id, customer, carrier, currency, f"hash-{authority_id}")


def finding(
    finding_id="f-1",
    invoice_id="inv-1",
    customer="cust-1",
    carrier="car-1",
    currency="USD",
    authority_id="auth-1",
    expected=10000,
    actual=12500,
    status=VALIDATED,
):
    return make_finding(
        finding_id=finding_id,
        invoice_id=invoice_id,
        customer_id=customer,
        carrier_id=carrier,
        currency=currency,
        authority_id=authority_id,
        expected_cents=expected,
        actual_cents=actual,
        status=status,
    )


def population(rows=None):
    return freeze_population(
        "buyer-1",
        "bu-1",
        "all paid invoices in 2026-08",
        rows or [row("inv-1", "shp-1")],
    )


def truth(findings=None, authorities=None, pop=None):
    pop = pop or population()
    return pop, freeze_truth(
        pop,
        authorities or [authority()],
        findings or [finding()],
    )


def test_population_hash_is_order_independent():
    rows = [row("inv-2", "shp-2"), row("inv-1", "shp-1")]
    a = population(rows)
    b = population(list(reversed(rows)))
    assert a.manifest_hash == b.manifest_hash


def test_duplicate_population_row_is_rejected():
    duplicate = row("inv-1", "shp-1")
    try:
        population([duplicate, duplicate])
    except ValueError as exc:
        assert "duplicate population row" in str(exc)
    else:
        raise AssertionError("duplicate row should fail")


def test_wrong_customer_or_carrier_authority_cannot_validate_money():
    pop = population()
    bad = authority(customer="different-customer")
    try:
        freeze_truth(pop, [bad], [finding()])
    except ValueError as exc:
        assert "authority identity mismatch" in str(exc)
    else:
        raise AssertionError("cross-customer authority should fail")


def test_review_case_asserts_zero_validated_dollars():
    pop = population()
    review = finding(status=REVIEW, authority_id=None, expected=10000, actual=15000)
    truth_manifest = freeze_truth(pop, [], [review])
    assert truth_manifest.findings[0].validated_cents == 0


def test_blind_protocol_requires_truth_before_incumbent_output():
    pop = population()
    try:
        open_incumbent_output(
            population=pop,
            truth=None,
            incumbent_population_hash=pop.manifest_hash,
            finding_ids=[],
        )
    except ValueError as exc:
        assert "truth must be frozen" in str(exc)
    else:
        raise AssertionError("incumbent output must stay sealed")


def test_incumbent_output_must_match_frozen_population():
    pop, truth_manifest = truth()
    try:
        open_incumbent_output(
            population=pop,
            truth=truth_manifest,
            incumbent_population_hash="wrong",
            finding_ids=[],
        )
    except ValueError as exc:
        assert "population hash mismatch" in str(exc)
    else:
        raise AssertionError("wrong population should fail")


def test_identical_same_dollar_findings_do_not_collapse():
    pop = population([row("inv-1", "shp-1"), row("inv-2", "shp-2")])
    findings = [
        finding("f-1", "inv-1", expected=10000, actual=12500),
        finding("f-2", "inv-2", expected=10000, actual=12500),
    ]
    truth_manifest = freeze_truth(pop, [authority()], findings)
    assert [item.finding_id for item in truth_manifest.findings] == ["f-1", "f-2"]
    assert sum(item.validated_cents for item in truth_manifest.findings) == 5000


def test_ambiguous_settlement_is_zero_realized():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    allocation = ledger.apply(
        SettlementEvent(
            "settle-1",
            "f-1",
            2500,
            "USD",
            "settlement-source-1",
            ambiguous_allocation=True,
        )
    )
    assert allocation.allocated_cents == 0
    assert ledger.certificate("f-1").realized_cents == 0


def test_duplicate_settlement_source_cannot_be_double_counted():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    ledger.apply(SettlementEvent("settle-1", "f-1", 1000, "USD", "source-hash-1"))
    try:
        ledger.apply(SettlementEvent("settle-2", "f-1", 1000, "USD", "source-hash-1"))
    except ValueError as exc:
        assert "source already consumed" in str(exc)
    else:
        raise AssertionError("same settlement source cannot be reused")


def test_partial_settlements_cap_at_validated_variance():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    first = ledger.apply(SettlementEvent("settle-1", "f-1", 1000, "USD", "source-1"))
    second = ledger.apply(SettlementEvent("settle-2", "f-1", 3000, "USD", "source-2"))
    cert = ledger.certificate("f-1")
    assert first.allocated_cents == 1000
    assert second.allocated_cents == 1500
    assert cert.validated_cents == 2500
    assert cert.realized_cents == 2500
    assert cert.fee_eligible_cents == 2500


def test_incumbent_preidentified_credit_is_not_fee_eligible():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    ledger.apply(
        SettlementEvent(
            "settle-1",
            "f-1",
            2500,
            "USD",
            "source-1",
            incumbent_preidentified=True,
        )
    )
    cert = ledger.certificate("f-1")
    assert cert.realized_cents == 2500
    assert cert.fee_eligible_cents == 0


def test_currency_mismatch_blocks_settlement():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    try:
        ledger.apply(SettlementEvent("settle-1", "f-1", 2500, "EUR", "source-1"))
    except ValueError as exc:
        assert "currency mismatch" in str(exc)
    else:
        raise AssertionError("cross-currency settlement should fail")


def test_recovery_certificate_is_bound_to_finding_and_settlement_proofs():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    ledger.apply(SettlementEvent("settle-1", "f-1", 2500, "USD", "source-1"))
    cert = ledger.certificate("f-1")
    assert cert.finding_proof_hash == truth_manifest.findings[0].proof_hash
    assert len(cert.settlement_proof_hashes) == 1
    assert cert.certificate_hash
