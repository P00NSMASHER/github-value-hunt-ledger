from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    RecoveryLedger,
    SettlementEvent,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
    REVIEW,
    VALIDATED,
)
from freight.pilot_reporting import (
    FindingReview,
    ReviewDisposition,
    build_pilot_metrics,
    render_markdown,
)


def setup_case():
    population = freeze_population(
        "buyer-1",
        "bu-1",
        "frozen period",
        [
            PopulationRow("inv-1","shp-1","cust","car","USD","src-1"),
            PopulationRow("inv-2","shp-2","cust","car","USD","src-2"),
            PopulationRow("inv-3","shp-3","cust","car","USD","src-3"),
        ],
    )
    authority = AuthorityRef("auth","cust","car","USD","auth-src")
    findings = [
        make_finding(
            finding_id="f-1", invoice_id="inv-1", customer_id="cust",
            carrier_id="car", currency="USD", authority_id="auth",
            expected_cents=10000, actual_cents=12500, status=VALIDATED,
        ),
        make_finding(
            finding_id="f-2", invoice_id="inv-2", customer_id="cust",
            carrier_id="car", currency="USD", authority_id="auth",
            expected_cents=10000, actual_cents=12500, status=VALIDATED,
        ),
        make_finding(
            finding_id="f-3", invoice_id="inv-3", customer_id="cust",
            carrier_id="car", currency="USD", authority_id=None,
            expected_cents=10000, actual_cents=15000, status=REVIEW,
        ),
    ]
    truth = freeze_truth(population, [authority], findings)
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        incumbent_population_hash=population.manifest_hash,
        finding_ids=["f-2"],
    )
    ledger = RecoveryLedger(truth, incumbent)
    return truth, incumbent, ledger


def test_pilot_report_keeps_all_financial_totals_separate():
    truth, incumbent, ledger = setup_case()
    ledger.apply(SettlementEvent("s-1","f-1",2000,"USD","settle-src-1"))
    ledger.apply(SettlementEvent("s-2","f-2",2500,"USD","settle-src-2"))

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

    assert metrics.reviewed_discrepancy_cents == 10000
    assert metrics.validated_finding_cents == 5000
    assert metrics.challenger_only_validated_cents == 2500
    assert metrics.realized_cents == 4500
    assert metrics.fee_eligible_realized_cents == 2000
    assert metrics.reviewer_minutes == 35


def test_incumbent_known_finding_is_automatically_non_fee_eligible():
    truth, incumbent, ledger = setup_case()
    allocation = ledger.apply(
        SettlementEvent("s-2","f-2",2500,"USD","settle-src-2")
    )
    assert allocation.allocated_cents == 2500
    assert allocation.fee_eligible_cents == 0


def test_recovery_ledger_rejects_incumbent_from_wrong_truth_manifest():
    truth, incumbent, _ = setup_case()
    tampered = incumbent.__class__(
        population_hash=incumbent.population_hash,
        truth_hash="wrong",
        finding_ids=incumbent.finding_ids,
        output_hash=incumbent.output_hash,
    )
    try:
        RecoveryLedger(truth, tampered)
    except ValueError as exc:
        assert "not bound to this truth" in str(exc)
    else:
        raise AssertionError("mismatched incumbent truth should fail")


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


def test_markdown_does_not_label_discrepancy_as_savings():
    truth, incumbent, ledger = setup_case()
    report = render_markdown(build_pilot_metrics(truth,incumbent,ledger))
    assert "Reviewed discrepancy" in report
    assert "Uniquely attributable realized" in report
    assert "Discrepancy and validated dollars are not realized savings" in report
