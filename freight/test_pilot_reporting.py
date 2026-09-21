import pytest

from freight.contracts import (
    AuthorityRef,
    IncumbentOutput,
    PopulationRow,
    RecoveryLedger,
    SettlementEvent,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
    seal_incumbent_submission,
    REVIEW,
    VALIDATED,
)
from freight.pilot_reporting import (
    FindingReview,
    ReviewDisposition,
    build_pilot_metrics,
    make_finding_review,
    render_markdown,
)


BUYER = "buyer-1"
BU = "bu-1"


def setup_case():
    population = freeze_population(
        BUYER,
        BU,
        "frozen period",
        [
            PopulationRow("inv-1","shp-1","cust","car","USD","src-1"),
            PopulationRow("inv-2","shp-2","cust","car","USD","src-2"),
            PopulationRow("inv-3","shp-3","cust","car","USD","src-3"),
        ],
    )
    authority = AuthorityRef("auth",BUYER,BU,"cust","car","USD","auth-src")
    findings = [
        make_finding(
            finding_id="f-1", buyer_id=BUYER, business_unit=BU,
            invoice_id="inv-1", shipment_id="shp-1", customer_id="cust",
            carrier_id="car", currency="USD", authority_id="auth",
            expected_cents=10000, actual_cents=12500, status=VALIDATED,
        ),
        make_finding(
            finding_id="f-2", buyer_id=BUYER, business_unit=BU,
            invoice_id="inv-2", shipment_id="shp-2", customer_id="cust",
            carrier_id="car", currency="USD", authority_id="auth",
            expected_cents=10000, actual_cents=12500, status=VALIDATED,
        ),
        make_finding(
            finding_id="f-3", buyer_id=BUYER, business_unit=BU,
            invoice_id="inv-3", shipment_id="shp-3", customer_id="cust",
            carrier_id="car", currency="USD", authority_id=None,
            expected_cents=10000, actual_cents=15000, status=REVIEW,
        ),
    ]
    truth = freeze_truth(population, [authority], findings)
    sealed = seal_incumbent_submission(population, "incumbent-source-hash")
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=["f-2"],
    )
    ledger = RecoveryLedger(truth, incumbent)
    return truth, incumbent, ledger


def settlement(settlement_id, finding_id, amount, source_hash):
    return SettlementEvent(
        buyer_id=BUYER,
        business_unit=BU,
        settlement_id=settlement_id,
        finding_id=finding_id,
        amount_cents=amount,
        currency="USD",
        source_hash=source_hash,
    )


def test_pilot_report_keeps_all_financial_totals_separate():
    truth, incumbent, ledger = setup_case()
    ledger.apply(settlement("s-1","f-1",2000,"settle-src-1"))
    ledger.apply(settlement("s-2","f-2",2500,"settle-src-2"))

    metrics = build_pilot_metrics(
        truth,
        incumbent,
        ledger,
        (
            FindingReview("f-1",ReviewDisposition.CONFIRMED,20),
            FindingReview("f-2",ReviewDisposition.CONFIRMED,10),
            FindingReview("f-3",ReviewDisposition.UNRESOLVED,5),
        ),
    )

    assert metrics.buyer_id == BUYER
    assert metrics.business_unit == BU
    assert metrics.reviewed_discrepancy_cents == 10000
    assert metrics.validated_finding_cents == 5000
    assert metrics.challenger_only_validated_cents == 2500
    assert metrics.realized_cents == 4500
    assert metrics.fee_eligible_realized_cents == 2000
    assert metrics.reviewer_minutes == 35


def test_incumbent_known_finding_is_automatically_non_fee_eligible():
    truth, incumbent, ledger = setup_case()
    allocation = ledger.apply(
        settlement("s-2","f-2",2500,"settle-src-2")
    )
    assert allocation.allocated_cents == 2500
    assert allocation.fee_eligible_cents == 0


def test_recovery_ledger_rejects_incumbent_from_wrong_scope():
    truth, incumbent, _ = setup_case()
    tampered = IncumbentOutput(
        buyer_id="buyer-2",
        business_unit=incumbent.business_unit,
        population_hash=incumbent.population_hash,
        truth_hash=incumbent.truth_hash,
        submission_hash=incumbent.submission_hash,
        source_hash=incumbent.source_hash,
        finding_ids=incumbent.finding_ids,
        output_hash=incumbent.output_hash,
    )
    try:
        RecoveryLedger(truth, tampered)
    except ValueError as exc:
        assert "incumbent output scope mismatch" in str(exc)
    else:
        raise AssertionError("mismatched incumbent scope should fail")


def test_false_positive_dollars_are_reported_not_hidden():
    truth, incumbent, ledger = setup_case()
    metrics = build_pilot_metrics(
        truth,
        incumbent,
        ledger,
        (FindingReview("f-1",ReviewDisposition.FALSE_POSITIVE,12),),
    )
    assert metrics.false_positive_count == 1
    assert metrics.false_positive_cents == 2500
    assert metrics.realized_cents == 0


def test_markdown_includes_scope_and_does_not_label_discrepancy_as_savings():
    truth, incumbent, ledger = setup_case()
    report = render_markdown(build_pilot_metrics(truth,incumbent,ledger))
    assert "Buyer scope: **buyer-1**" in report
    assert "Business unit: **bu-1**" in report
    assert "Reviewed discrepancy" in report
    assert "Settlement-proven realized" in report
    assert "Discrepancy and validated dollars are not realized savings" in report


def frozen_case(*, currency="USD", expected=10000, status=VALIDATED, incumbent_ids=()):
    population = freeze_population("buyer", "unit", "two synthetic invoices", [
        PopulationRow(f"i{i}", f"s{i}", "customer", "carrier", currency, f"source-{i}")
        for i in range(2)
    ])
    authority = AuthorityRef("authority", "buyer", "unit", "customer", "carrier", currency, "authority-source")
    findings = [make_finding(
        finding_id=f"f{i}", buyer_id="buyer", business_unit="unit", invoice_id=f"i{i}",
        shipment_id=f"s{i}", customer_id="customer", carrier_id="carrier", currency=currency,
        authority_id="authority" if status == VALIDATED else None,
        expected_cents=expected, actual_cents=12500, status=status,
    ) for i in range(2)]
    truth = freeze_truth(population, [authority], findings)
    incumbent = open_incumbent_output(
        population=population, truth=truth,
        submission=seal_incumbent_submission(population, "incumbent-source"), finding_ids=incumbent_ids,
    )
    return truth, incumbent


def settled_ledger(truth, incumbent=None):
    ledger = RecoveryLedger(truth, incumbent)
    ledger.apply(SettlementEvent("buyer", "unit", "settlement", "f0", 1000, "USD", "settlement-source"))
    return ledger


def test_report_accepts_bound_settlement_and_preserves_financial_totals():
    truth, incumbent = frozen_case()
    metrics = build_pilot_metrics(truth, incumbent, settled_ledger(truth, incumbent))
    assert metrics.validated_finding_cents == 5000
    assert metrics.realized_cents == 1000
    assert metrics.fee_eligible_realized_cents == 1000


def test_same_buyer_ledger_from_other_frozen_finding_is_rejected():
    truth, incumbent = frozen_case()
    different_truth, _ = frozen_case(expected=9000)
    with pytest.raises(ValueError, match="frozen finding proof"):
        build_pilot_metrics(truth, incumbent, settled_ledger(different_truth))


def test_incumbent_fee_attribution_is_checked_per_finding_not_aggregate():
    truth, incumbent = frozen_case(incumbent_ids=("f0",))
    # The other finding leaves enough aggregate challenger capacity to hide
    # a fee assigned to the incumbent finding unless attribution is per finding.
    with pytest.raises(ValueError, match="incumbent finding"):
        build_pilot_metrics(truth, incumbent, settled_ledger(truth))


def test_incumbent_bound_ledger_reports_zero_success_fee_for_its_findings():
    truth, incumbent = frozen_case(incumbent_ids=("f0",))
    metrics = build_pilot_metrics(truth, incumbent, settled_ledger(truth, incumbent))
    assert metrics.realized_cents == 1000
    assert metrics.fee_eligible_realized_cents == 0
    report = render_markdown(metrics)
    assert "Settlement-proven realized" in report
    assert "Uniquely attributable realized" not in report


def test_non_usd_amounts_cannot_be_reported_as_dollars():
    truth, incumbent = frozen_case(currency="EUR")
    with pytest.raises(ValueError, match="USD"):
        build_pilot_metrics(truth, incumbent, RecoveryLedger(truth, incumbent))


def test_review_only_false_positive_preserves_the_flagged_amount():
    truth, incumbent = frozen_case(status=REVIEW)
    metrics = build_pilot_metrics(truth, incumbent, RecoveryLedger(truth, incumbent), (
        FindingReview("f0", ReviewDisposition.FALSE_POSITIVE, 3),
    ))
    assert metrics.validated_finding_cents == 0
    assert metrics.false_positive_count == 1
    assert metrics.false_positive_cents == 2500


def test_untyped_review_disposition_cannot_be_silently_ignored():
    with pytest.raises(ValueError, match="ReviewDisposition"):
        FindingReview("f0", "FALSE_POSITIVE", 3)


def test_bound_review_rejects_stale_finding_proof_in_reporting():
    truth, incumbent, ledger = setup_case()
    review = make_finding_review(
        truth.findings[0],
        ReviewDisposition.CONFIRMED,
        reviewer_role="Buyer Controller",
        reviewed_at="2026-09-21T12:00:00Z",
        reviewer_minutes=4,
    )
    object.__setattr__(review, "finding_proof_hash", "0" * 64)
    with pytest.raises(ValueError, match="proof hash"):
        build_pilot_metrics(truth, incumbent, ledger, (review,))


def test_bound_review_normalizes_timestamp_and_has_deterministic_hash():
    truth, _, _ = setup_case()
    a = make_finding_review(
        truth.findings[0],
        ReviewDisposition.CONFIRMED,
        reviewer_role=" Buyer Controller ",
        reviewed_at="2026-09-21T08:00:00-04:00",
        reviewer_minutes=4,
    )
    b = make_finding_review(
        truth.findings[0],
        ReviewDisposition.CONFIRMED,
        reviewer_role="Buyer Controller",
        reviewed_at="2026-09-21T12:00:00Z",
        reviewer_minutes=4,
    )
    assert a.reviewed_at == "2026-09-21T12:00:00.000000Z"
    assert a.review_hash == b.review_hash
