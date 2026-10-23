"""RETALLY authentic-public fact boundaries and synthetic-engine test matrix."""
from hashlib import sha256
from decimal import Decimal
import pytest

from freight.public_freight_corpus import (
    SOURCES, SEC_LANES, source, require_reuse, catalog_sha256,
    historical_gao_arithmetic, historical_bulk_probe,
    intermodal_probe, kentucky_numeric_fact_and_reconciliation_hold,
    aggregate_research_receipt,
)
from freight.sealed_real_accuracy import (
    ModelCall, PredictionSeal, TruthCall, TruthSeal,
    prediction_seal_hash, truth_seal_hash, score_sealed_freight,
)


def digest(s):
    return sha256(s.encode("utf-8")).hexdigest()


def test_five_authentic_public_source_leads_and_no_original_document_bytes():
    assert len(SOURCES) == 5
    assert len({s.key for s in SOURCES}) == 5
    assert len(catalog_sha256()) == 64
    assert catalog_sha256() == catalog_sha256()
    assert {s.key for s in SOURCES} == {
        "SEC_BULK_2007", "SEC_INTERMODAL_2013", "GAO_B160344",
        "OD_FUEL_2026", "KENTUCKY_PSC_2024",
    }
    assert all(s.original_bytes_sha256 is None for s in SOURCES)
    assert all(not s.verified_bank_source for s in SOURCES)
    assert all(not s.commercial_recovery_authorized for s in SOURCES)
    assert all("@" not in s.url and "%40" not in s.url for s in SOURCES)


@pytest.mark.parametrize("key", [
    "SEC_BULK_2007", "SEC_INTERMODAL_2013", "GAO_B160344",
])
def test_official_reusable_documents_still_do_not_grant_customer_data_rights(key):
    require_reuse(key)
    with pytest.raises(PermissionError, match="private"):
        require_reuse(key, import_original=True)
    with pytest.raises(PermissionError, match="commercial"):
        require_reuse(key, commercial_distribution=True)


@pytest.mark.parametrize("key", ["OD_FUEL_2026", "KENTUCKY_PSC_2024"])
def test_nonlicensed_originals_are_metadata_only(key):
    with pytest.raises(PermissionError, match="metadata-only"):
        require_reuse(key)
    with pytest.raises(PermissionError, match="private"):
        require_reuse(key, import_original=True)
    assert not source(key).commercial_recovery_authorized


def test_unknown_source_rejected_and_locator_is_not_document_sha256():
    with pytest.raises(ValueError, match="allowlist"):
        source("FAKE_EXTERNAL_FREIGHT_DOCUMENT")
    assert source("KENTUCKY_PSC_2024").permission_url is None
    assert source("OD_FUEL_2026").permission == "INFORMATIONAL_ONLY"
    assert source("SEC_BULK_2007").url_sha256 != catalog_sha256()


def test_1967_public_gao_claimed_allowed_historical_deduction():
    case = historical_gao_arithmetic()
    assert case["claimed_cents"] == 27517
    assert case["allowed_cents"] == 13929
    assert case["historical_offset_cents"] == 13588
    assert case["retally_recovered_cents"] == 0
    assert case["modern_invoice_adjudicated"] is False


def test_independently_labeled_1967_case_cannot_label_unrelated_synthetic_invoice():
    m = ModelCall(
        "SYNTHETIC-UNRELATED-BUYER-CASE", "POSITIVE", 13588,
        digest("synthetic model output, not official GAO invoice"),
    )
    truth = TruthCall(
        case_id=m.case_id, truth_label="UNRESOLVED",
        adjudicated_overcharge_cents=0,
        original_invoice_sha256=digest("synthetic invoice placeholder"),
        applicable_rate_sha256=None, bank_payment_sha256=None,
        adjudication_sha256=digest("historical unrelated legal precedent"),
        source_complete=False,
    )
    model_at = "2026-10-21T14:00:00Z"
    truth_at = "2026-10-21T15:00:00Z"
    model = PredictionSeal(
        "SYN-MODEL", model_at, (m,),
        prediction_seal_hash("SYN-MODEL", model_at, (m,)),
    )
    t = TruthSeal(
        "SYN-TRUTH", "SYN-REVIEWER-1", "SYN-REVIEWER-2", truth_at,
        (truth,), truth_seal_hash(
            "SYN-TRUTH", "SYN-REVIEWER-1", "SYN-REVIEWER-2",
            truth_at, (truth,),
        ),
    )
    report = score_sealed_freight(
        model, t, joint_unseal_at="2026-10-22T00:00:00Z",
        study_kind="SYNTHETIC_REHEARSAL",
    )
    assert report.population_count == 1
    assert report.unresolved_truth_count == 1
    assert report.complete_independent_truth_count == 0
    assert report.scored_automatic_decisions == 0
    assert report.precision is None
    assert report.publication_claim_approved is False


def test_real_sec_bulk_price_on_explicitly_synthetic_gallon_count():
    no_fuel = historical_bulk_probe(1000)
    fuel = historical_bulk_probe(1000, "0.0003")
    assert no_fuel["base_cents"] == 1299
    assert no_fuel["fuel_cents"] == 0
    assert fuel["fuel_cents"] == 30
    assert fuel["scenario_total_cents"] == 1329
    assert fuel["verified_new_recovery_cents"] == 0
    for bad in (0, -1, True, Decimal("1.5"), 10**40):
        with pytest.raises(ValueError):
            historical_bulk_probe(bad)
    with pytest.raises(ValueError, match="unpublished"):
        historical_bulk_probe(1000, "0.00031")


@pytest.mark.parametrize("lane", sorted(SEC_LANES))
def test_actual_retail_rating_and_strict_evidence_review_of_historical_sec_lanes(lane):
    origin, destination, cents = SEC_LANES[lane]
    modeled, strict = intermodal_probe(
        lane=lane, origin=origin, destination=destination,
        service_date="2013-10-15", billed_cents=cents,
    )
    assert modeled.expected_total_cents == cents
    assert modeled.billed_total_cents == cents
    assert modeled.variance_cents == 0
    assert modeled.status == "REVIEW_REQUIRED"
    assert "AUTHORITY_NOT_HUMAN_VERIFIED" in modeled.blockers
    assert strict.status == "REVIEW_REQUIRED"
    assert strict.externally_verified_freight_error_cents is None
    assert strict.externally_verified_cash_recovered_cents == 0
    assert strict.independent_accuracy_scored is False
    assert "INDEPENDENT_SHIPMENT_DOCUMENT_MISSING" in strict.blockers
    assert "BANK_CLEARED_PAYMENT_NOT_INDEPENDENTLY_VERIFIED" in strict.blockers
    assert "RATE_AUTHORITY_NOT_VERIFIED" in strict.blockers


def test_public_fuel_inclusive_rate_blocks_extra_fuel_in_study_expected_price():
    origin, destination, cents = SEC_LANES["CRANBURY_CHINO"]
    modeled, strict = intermodal_probe(
        lane="CRANBURY_CHINO", origin=origin, destination=destination,
        service_date="2013-10-15", billed_cents=cents + 20000,
    )
    assert modeled.expected_total_cents == cents
    assert modeled.variance_cents == 20000  # fabricated challenge amount only
    assert modeled.status == "REVIEW_REQUIRED"
    assert strict.provisional_variance_cents is None
    assert strict.externally_verified_cash_recovered_cents == 0
    assert sum(x.expected_cents for x in modeled.components if x.code == "FUEL") == 0


@pytest.mark.parametrize("lane,origin,destination,date", [
    ("KENTWOOD_CHINO", "CRANBURY_NJ", "CHINO_CA", "2013-10-15"),
    ("CRANBURY_CHINO", "CRANBURY_NJ", "KENTWOOD_MI", "2013-10-15"),
    ("CRANBURY_CHINO", "CRANBURY_NJ", "CHINO_CA", "2026-10-22"),
    ("UNREGISTERED", "CRANBURY_NJ", "CHINO_CA", "2013-10-15"),
])
def test_disputed_date_and_cross_lane_rates_fail_closed(lane, origin, destination, date):
    with pytest.raises(ValueError):
        intermodal_probe(
            lane=lane, origin=origin, destination=destination,
            service_date=date, billed_cents=230000,
        )


def test_2024_kentucky_freight_expense_numbers_are_not_bank_or_overcharge():
    facts = kentucky_numeric_fact_and_reconciliation_hold()
    assert facts["published_charge_cents"] == 18400
    assert facts["published_expense_cents"] == 20056
    assert facts["expense_markup_cents_not_carrier_overcharge"] == 1656
    assert facts["original_pdf_ingested"] is False
    assert facts["bank_matches"] == 0
    assert facts["verified_new_recovery_cents"] == 0


def test_aggregate_report_says_no_new_recovery_and_no_independent_accuracy():
    result = aggregate_research_receipt()
    assert result["source_leads"] == 5
    assert result["official_reusable_source_leads"] == 3
    assert result["rights_restricted_source_leads"] == 2
    assert len(result["intermodal_engine_probe_results"]) == 2
    assert result["historical_gao_arithmetic_valid"]
    assert result["synthetic_bulk_scenario_total_cents"] == 1329
    assert result["source_document_byte_hashes_verified"] == 0
    assert result["actual_customer_documents_ingested"] == 0
    assert result["verified_new_customer_recovery_cents"] == 0
    assert result["billable_customer_fee_cents"] == 0
    assert result["real_precision"] is None and result["real_recall"] is None
    assert all(row["rated_state"] == "REVIEW_REQUIRED"
               and row["evidence_state"] == "REVIEW_REQUIRED"
               and row["verified_recovered_cents"] == 0
               for row in result["intermodal_engine_probe_results"])
