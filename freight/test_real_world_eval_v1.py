"""Offline v1 public freight benchmark regression and leakage controls."""
from copy import deepcopy
from datetime import date

import pytest

from freight.real_world_eval_v1 import (
    EXPECTED_IDS, aggregate_receipt, big_g_face_arithmetic,
    evergreen_reference, gibson_reference, load_manifest, marine_study_quote,
    native_engine_invoice_hold, pyle_face_arithmetic, tesoro_study_quote,
    validate_manifest,
)


@pytest.fixture
def cases():
    return validate_manifest(load_manifest())


def test_population_is_frozen_and_not_real_customer_truth(cases):
    assert set(cases) == EXPECTED_IDS
    assert len(cases) == 9
    assert sum(c["category"] == "PUBLIC_INVOICE_FACE" for c in cases.values()) == 2
    assert sum(c["category"] == "OFFICIAL_ADJUDICATION_REFERENCE" for c in cases.values()) == 3
    assert all(c["original_bytes_sha256"] is None for c in cases.values())
    assert all(c["real_customer_payment_verified"] is False for c in cases.values())
    assert all(c["controlling_customer_rate_verified"] is False for c in cases.values())
    assert all(c["expected_action"] != "APPROVE_CLAIM" for c in cases.values())


def test_invoice_face_arithmetic_exact_and_not_buyer_rate_adjudication(cases):
    pyle = pyle_face_arithmetic(cases)
    assert pyle == {"total_cents": 19492, "fuel_cents": 1720,
                    "rate_verified": False}
    big_g = big_g_face_arithmetic(cases)
    assert big_g == {"total_cents": 43716, "bill_before_ship_days": 9,
                     "actual_overcharge_established": False}
    assert date.fromisoformat(cases["PYLE_2021_FACE"]["facts"]["invoice_date"]) > date.fromisoformat(
        cases["PYLE_2021_FACE"]["facts"]["shipment_date"])


@pytest.mark.parametrize("case_id", ["BIG_G_2026_FACE", "PYLE_2021_FACE"])
def test_actual_freight_engine_fails_closed_for_public_invoice_numbers(cases, case_id):
    result = native_engine_invoice_hold(cases, case_id)
    assert result["rated_status"] == "REVIEW_REQUIRED"
    assert result["evidence_status"] == "REVIEW_REQUIRED"
    assert result["verified_new_recovery_cents"] == 0


def test_official_positive_and_negative_legal_references_do_not_become_new_claims(cases):
    evergreen = evergreen_reference(cases)
    assert evergreen == {"adjudicated_case_dispute_cents": 51000,
                         "new_retally_recovery_cents": 0}
    assert cases["EVERGREEN_TCW_2026_COURT"]["facts"]["invoice_detention_cents"] == 149000
    gibson = gibson_reference(cases)
    assert gibson["published_reparations_cents"] == 866879
    assert gibson["published_interest_cents"] == 98572
    assert gibson["published_award_cents"] == 965451
    assert gibson["independently_verified_customer_invoice_overcharge_cents"] is None
    bakerly = cases["BAKERLY_SEAFRIGO_FMC"]
    assert bakerly["expected_action"] == "LEGAL_NEGATIVE_CONTROL"
    assert bakerly["facts"]["disposition"] == "SHIPPING_ACT_CLAIMS_DISMISSED"
    assert bakerly["facts"]["meaning"] == "DO_NOT_INFER_OVERCHARGE_OR_EVERY_CHARGE_VALID"


@pytest.mark.parametrize("prior,expected_cents", [
    (699900, 32000), (699950, 29750), (700000, 27500),
])
def test_real_published_tesoro_rates_synthetic_threshold_split(cases, prior, expected_cents):
    assert tesoro_study_quote(cases, miles=45, barrels=100,
                              prior_month_barrels=prior) == expected_cents


@pytest.mark.parametrize("miles", [0, 40, 46, 68, 70, 100])
def test_tesoro_unknown_or_overlapping_mileage_fails_closed(cases, miles):
    with pytest.raises(ValueError):
        tesoro_study_quote(cases, miles=miles, barrels=100,
                           prior_month_barrels=0)


@pytest.mark.parametrize("miles,barrels,prior", [
    (45, 0, 0), (45, -1, 0), (45, True, 0),
    (45, 100, -1), (45, 100, True), (45.5, 100, 0),
])
def test_tesoro_invalid_synthetic_inputs_fail_closed(cases, miles, barrels, prior):
    with pytest.raises(ValueError):
        tesoro_study_quote(cases, miles=miles, barrels=barrels,
                           prior_month_barrels=prior)


def test_real_published_marine_rates_are_partial_study_only(cases):
    assert marine_study_quote(cases, equipment="C2", days=3) == 301800
    assert marine_study_quote(cases, equipment="H3", days=3) == 722400
    assert marine_study_quote(cases, equipment="B1", days=1) == 609400
    for equipment, days in (("UNKNOWN", 1), ("C2", 0), ("H3", True), ("B1", 366)):
        with pytest.raises(ValueError):
            marine_study_quote(cases, equipment=equipment, days=days)


def test_rail_and_fuel_are_not_secret_invoice_truth(cases):
    rail = cases["STB_2024_WAYBILL"]["facts"]
    assert rail["sample_year"] == 2024
    assert rail["revenue_may_be_masked"] is True
    assert rail["real_shipments_ingested"] == 0
    fuel = cases["EIA_DIESEL_HISTORY"]["facts"]
    assert fuel["raw_price_observations_ingested"] == 0
    assert fuel["diesel_prices_do_not_prove_carrier_fuel_formula"] is True


@pytest.mark.parametrize("change", [
    lambda m: m["policies"].update(original_documents_included=True),
    lambda m: m["policies"].update(verified_customer_recovered_cents=1),
    lambda m: m["cases"][0].update(original_bytes_sha256="a" * 64),
    lambda m: m["cases"][0].update(real_customer_payment_verified=True),
    lambda m: m["cases"][0].update(expected_action="APPROVE_CLAIM"),
    lambda m: m["cases"][0].update(source_url="https://example.org/thirdparty"),
    lambda m: m["cases"][0].update(source_url="https://extranet4.biggexpress.com/?id=confidential"),
    lambda m: m["cases"][0]["facts"].update(invoice_number="customer-pro"),
    lambda m: m["cases"][0].update(locator_policy="PUBLIC_FULL_INVOICE_URL"),
    lambda m: m["cases"].append(deepcopy(m["cases"][0])),
])
def test_mutated_rights_privacy_truth_and_population_are_rejected(change):
    m = deepcopy(load_manifest())
    change(m)
    with pytest.raises(ValueError):
        validate_manifest(m)


def test_aggregate_receipt_never_claims_revenue_accuracy_or_approved_launch():
    summary = aggregate_receipt()
    assert summary["pack_version"] == "1.0.0"
    assert summary["public_real_world_source_leads"] == 9
    assert len(summary["fixture_metadata_sha256_not_original_document"]) == 64
    assert summary["original_documents_ingested"] == 0
    assert summary["verified_new_customer_overcharge_cents"] is None
    assert summary["verified_new_customer_recovery_cents"] == 0
    assert summary["billable_fees_cents"] == 0
    assert summary["blind_real_precision"] is None
    assert summary["blind_real_recall"] is None
    assert summary["commercial_release_approved"] is False
