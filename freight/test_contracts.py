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
    seal_incumbent_submission,
)


BUYER = "buyer-1"
BU = "bu-1"


def row(invoice, shipment, customer="cust-1", carrier="car-1", currency="USD", source="src"):
    return PopulationRow(invoice, shipment, customer, carrier, currency, f"{source}-{invoice}-{shipment}")


def authority(
    authority_id="auth-1",
    buyer=BUYER,
    bu=BU,
    customer="cust-1",
    carrier="car-1",
    currency="USD",
):
    return AuthorityRef(
        authority_id,
        buyer,
        bu,
        customer,
        carrier,
        currency,
        f"hash-{authority_id}",
    )


def finding(
    finding_id="f-1",
    invoice_id="inv-1",
    shipment_id="shp-1",
    buyer=BUYER,
    bu=BU,
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
        buyer_id=buyer,
        business_unit=bu,
        invoice_id=invoice_id,
        shipment_id=shipment_id,
        customer_id=customer,
        carrier_id=carrier,
        currency=currency,
        authority_id=authority_id,
        expected_cents=expected,
        actual_cents=actual,
        status=status,
    )


def population(rows=None, buyer=BUYER, bu=BU):
    return freeze_population(
        buyer,
        bu,
        "all paid invoices in 2026-08",
        rows or [row("inv-1", "shp-1")],
    )


def truth(findings=None, authorities=None, pop=None):
    pop = pop or population()
    return pop, freeze_truth(
        pop,
        authorities or [authority(buyer=pop.buyer_id, bu=pop.business_unit)],
        findings or [finding(buyer=pop.buyer_id, bu=pop.business_unit)],
    )


def settlement(
    settlement_id="settle-1",
    finding_id="f-1",
    amount=2500,
    currency="USD",
    source_hash="source-1",
    buyer=BUYER,
    bu=BU,
    **kwargs,
):
    return SettlementEvent(
        buyer_id=buyer,
        business_unit=bu,
        settlement_id=settlement_id,
        finding_id=finding_id,
        amount_cents=amount,
        currency=currency,
        source_hash=source_hash,
        **kwargs,
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


def test_wrong_buyer_authority_cannot_validate_money():
    pop = population()
    bad = authority(buyer="buyer-2")
    try:
        freeze_truth(pop, [bad], [finding()])
    except ValueError as exc:
        assert "authority scope mismatch" in str(exc)
    else:
        raise AssertionError("cross-buyer authority should fail")


def test_wrong_business_unit_finding_cannot_enter_truth():
    pop = population()
    try:
        freeze_truth(pop, [authority()], [finding(bu="other-bu")])
    except ValueError as exc:
        assert "finding scope mismatch" in str(exc)
    else:
        raise AssertionError("cross-BU finding should fail")


def test_same_invoice_wrong_shipment_cannot_attach_to_population():
    pop = population([row("inv-1", "shp-1"), row("inv-1", "shp-2")])
    try:
        freeze_truth(pop, [authority()], [finding(shipment_id="shp-3")])
    except ValueError as exc:
        assert "finding outside frozen population" in str(exc)
    else:
        raise AssertionError("wrong shipment should fail")


def test_finding_identity_must_match_frozen_shipment_row():
    pop = population([row("inv-1", "shp-1", customer="cust-a")])
    try:
        freeze_truth(
            pop,
            [authority(customer="cust-b")],
            [finding(customer="cust-b")],
        )
    except ValueError as exc:
        assert "finding identity mismatch" in str(exc)
    else:
        raise AssertionError("finding identity must match frozen row")


def test_review_case_asserts_zero_validated_dollars():
    pop = population()
    review = finding(status=REVIEW, authority_id=None, expected=10000, actual=15000)
    truth_manifest = freeze_truth(pop, [], [review])
    assert truth_manifest.findings[0].validated_cents == 0


def test_incumbent_submission_can_be_sealed_before_truth_exists():
    pop = population()
    sealed = seal_incumbent_submission(pop, "incumbent-file-sha")
    assert sealed.population_hash == pop.manifest_hash
    assert sealed.sealed_hash


def test_blind_protocol_requires_truth_before_incumbent_output_opens():
    pop = population()
    sealed = seal_incumbent_submission(pop, "incumbent-file-sha")
    try:
        open_incumbent_output(
            population=pop,
            truth=None,
            submission=sealed,
            finding_ids=[],
        )
    except ValueError as exc:
        assert "truth must be frozen" in str(exc)
    else:
        raise AssertionError("incumbent output must stay sealed")


def test_incumbent_submission_must_match_frozen_population_scope():
    pop, truth_manifest = truth()
    other = population(buyer="buyer-2")
    sealed = seal_incumbent_submission(other, "incumbent-file-sha")
    try:
        open_incumbent_output(
            population=pop,
            truth=truth_manifest,
            submission=sealed,
            finding_ids=[],
        )
    except ValueError as exc:
        assert "incumbent submission scope mismatch" in str(exc)
    else:
        raise AssertionError("wrong buyer incumbent submission should fail")


def test_identical_same_dollar_findings_do_not_collapse():
    pop = population([row("inv-1", "shp-1"), row("inv-2", "shp-2")])
    findings = [
        finding("f-1", "inv-1", "shp-1", expected=10000, actual=12500),
        finding("f-2", "inv-2", "shp-2", expected=10000, actual=12500),
    ]
    truth_manifest = freeze_truth(pop, [authority()], findings)
    assert [item.finding_id for item in truth_manifest.findings] == ["f-1", "f-2"]
    assert sum(item.validated_cents for item in truth_manifest.findings) == 5000


def test_ambiguous_settlement_is_zero_realized():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    allocation = ledger.apply(
        settlement(
            source_hash="settlement-source-1",
            ambiguous_allocation=True,
        )
    )
    assert allocation.allocated_cents == 0
    assert ledger.certificate("f-1").realized_cents == 0


def test_wrong_buyer_settlement_is_rejected():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    try:
        ledger.apply(settlement(buyer="buyer-2"))
    except ValueError as exc:
        assert "settlement scope mismatch" in str(exc)
    else:
        raise AssertionError("cross-buyer settlement should fail")


def test_duplicate_settlement_source_cannot_be_double_counted():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    ledger.apply(settlement("settle-1", amount=1000, source_hash="source-hash-1"))
    try:
        ledger.apply(settlement("settle-2", amount=1000, source_hash="source-hash-1"))
    except ValueError as exc:
        assert "source already consumed" in str(exc)
    else:
        raise AssertionError("same settlement source cannot be reused")


def test_partial_settlements_cap_at_validated_variance():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    first = ledger.apply(settlement("settle-1", amount=1000, source_hash="source-1"))
    second = ledger.apply(settlement("settle-2", amount=3000, source_hash="source-2"))
    cert = ledger.certificate("f-1")
    assert first.allocated_cents == 1000
    assert second.allocated_cents == 1500
    assert cert.validated_cents == 2500
    assert cert.realized_cents == 2500
    assert cert.fee_eligible_cents == 2500
    assert cert.buyer_id == BUYER
    assert cert.business_unit == BU


def test_incumbent_preidentified_credit_is_not_fee_eligible():
    pop, truth_manifest = truth()
    sealed = seal_incumbent_submission(pop, "incumbent-file-sha")
    incumbent = open_incumbent_output(
        population=pop,
        truth=truth_manifest,
        submission=sealed,
        finding_ids=["f-1"],
    )
    ledger = RecoveryLedger(truth_manifest, incumbent)
    ledger.apply(settlement())
    cert = ledger.certificate("f-1")
    assert cert.realized_cents == 2500
    assert cert.fee_eligible_cents == 0


def test_currency_mismatch_blocks_settlement():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    try:
        ledger.apply(settlement(currency="EUR"))
    except ValueError as exc:
        assert "currency mismatch" in str(exc)
    else:
        raise AssertionError("cross-currency settlement should fail")


def test_recovery_certificate_is_bound_to_scope_finding_and_settlement_proofs():
    _, truth_manifest = truth()
    ledger = RecoveryLedger(truth_manifest)
    ledger.apply(settlement())
    cert = ledger.certificate("f-1")
    assert cert.buyer_id == BUYER
    assert cert.business_unit == BU
    assert cert.finding_proof_hash == truth_manifest.findings[0].proof_hash
    assert len(cert.settlement_proof_hashes) == 1
    assert cert.certificate_hash


def test_frozen_truth_binds_authority_source_evidence():
    pop = population()
    one = freeze_truth(pop, [authority()], [finding()])
    changed = freeze_truth(
        pop,
        [AuthorityRef("auth-1", BUYER, BU, "cust-1", "car-1", "USD", "changed-source")],
        [finding()],
    )
    assert one.authorities[0].source_hash != changed.authorities[0].source_hash
    assert one.truth_hash != changed.truth_hash


def test_clean_truth_manifest_is_valid_and_deterministic():
    pop = population()
    a = freeze_truth(pop, [], [])
    b = freeze_truth(pop, [], [])
    assert a.findings == ()
    assert a.authorities == ()
    assert a.truth_hash == b.truth_hash
