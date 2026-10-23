"""Offline, privacy-safe real-world freight evaluation pack v1.

Actual public invoice *numbers*, official legal outcomes and published rate
anchors are deliberately kept separate. Shipment records are fabricated,
not imported originals. No claim, cash recovery or buyer-rate authority may
be inferred from this study.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.priority2_evidence import review_freight_rate
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "real_world_eval_v1.json"
EXPECTED_IDS = frozenset({
    "BIG_G_2026_FACE", "PYLE_2021_FACE", "EVERGREEN_TCW_2026_COURT",
    "GIBSON_FMC_2030I", "BAKERLY_SEAFRIGO_FMC", "TESORO_2011_TRUCKING",
    "MARATHON_2026_MARINE", "STB_2024_WAYBILL", "EIA_DIESEL_HISTORY",
})
OFFICIAL_HOSTS = frozenset({
    "extranet4.biggexpress.com", "cw.shipandsave.com",
    "media.cadc.uscourts.gov", "www2.fmc.gov", "www.fmc.gov",
    "www.sec.gov", "www.stb.gov", "www.eia.gov",
})
PROHIBITED_FACT_KEYS = frozenset({
    "invoice_number", "pro_number", "bill_of_lading_number",
    "bank_account", "payment_account", "customer_name", "customer_address",
    "original_pdf", "pdf_text", "document_url", "document_bytes",
})


def load_manifest() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict) -> dict[str, dict]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0.0":
        raise ValueError("unsupported benchmark schema")
    policies = manifest.get("policies")
    if not isinstance(policies, dict) or any(policies.get(k) is not False for k in (
        "original_documents_included", "customer_data_included",
        "commercial_processing_authorized", "external_action_authorized",
        "source_byte_sha256_available", "independent_accuracy_scoring_authorized",
    )) or policies.get("verified_customer_recovered_cents") != 0:
        raise ValueError("public source study may not promote customer data or recovery proof")

    rows = manifest.get("cases")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_IDS):
        raise ValueError("benchmark case population drift")
    by_id = {x.get("id"): x for x in rows if isinstance(x, dict)}
    if len(by_id) != len(rows) or set(by_id) != EXPECTED_IDS:
        raise ValueError("missing, duplicate or unknown case identifier")
    for row in rows:
        url = urlsplit(row.get("source_url", ""))
        if (url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS
                or url.username or url.password or url.query or url.fragment):
            raise ValueError("unsafe or unpublished source locator")
        if (row.get("original_bytes_sha256") is not None
                or row.get("real_customer_payment_verified") is not False
                or row.get("controlling_customer_rate_verified") is not False):
            raise ValueError("public facts are not customer evidence")
        if row.get("expected_action") not in {
            "REVIEW_REQUIRED", "LEGAL_REFERENCE_ONLY", "LEGAL_NEGATIVE_CONTROL",
            "SYNTHETIC_PRICE_MODEL_ONLY", "VOLUME_ONLY_NO_RATE_TRUTH",
            "CONTEXT_ONLY_NOT_A_BUYER_CONTRACT",
        }:
            raise ValueError("unexpected automatic action")
        facts = row.get("facts")
        if not isinstance(facts, dict) or PROHIBITED_FACT_KEYS.intersection(facts):
            raise ValueError("original invoice identifiers or customer data not permitted")
        if row["category"] == "PUBLIC_INVOICE_FACE" and (
            row.get("locator_policy") != "INVOICE_SPECIFIC_URL_WITHHELD_FROM_PUBLIC_REPO"
            or row["expected_action"] != "REVIEW_REQUIRED"
        ):
            raise ValueError("third-party invoice pointers must remain withheld")
    return by_id


def fixture_sha256() -> str:
    """Digest of our *curated fixture bytes*, never of original documents."""
    return sha256(FIXTURE_PATH.read_bytes()).hexdigest()


def _case(by_id: dict[str, dict], key: str) -> dict:
    return by_id[key]["facts"]


def pyle_face_arithmetic(by_id: dict[str, dict]) -> dict:
    f = _case(by_id, "PYLE_2021_FACE")
    fuel = int((Decimal(f["linehaul_cents"]) * Decimal(f["fuel_rate_bps"])
                / Decimal(10000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total = f["linehaul_cents"] + f["liftgate_cents"] + f["fuel_cents"]
    if fuel != f["fuel_cents"] or total != f["total_cents"]:
        raise AssertionError("real published Pyle invoice-face money changed")
    return {"total_cents": total, "fuel_cents": fuel, "rate_verified": False}


def big_g_face_arithmetic(by_id: dict[str, dict]) -> dict:
    f = _case(by_id, "BIG_G_2026_FACE")
    if f["linehaul_cents"] + f["fuel_cents"] != f["total_cents"]:
        raise AssertionError("real published Big G invoice-face sum changed")
    days = (date.fromisoformat(f["shipment_date"])
            - date.fromisoformat(f["invoice_date"])).days
    if days != 9:
        raise AssertionError("published bill-before-ship date anomaly changed")
    return {"total_cents": f["total_cents"], "bill_before_ship_days": days,
            "actual_overcharge_established": False}


def evergreen_reference(by_id: dict[str, dict]) -> dict:
    f = _case(by_id, "EVERGREEN_TCW_2026_COURT")
    disputed = f["port_closed_days"] * (f["container_daily_cents"] + f["chassis_daily_cents"])
    if disputed != f["disputed_cents"] or disputed > f["invoice_detention_cents"]:
        raise AssertionError("Evergreen published decision arithmetic changed")
    return {"adjudicated_case_dispute_cents": disputed,
            "new_retally_recovery_cents": 0}


def gibson_reference(by_id: dict[str, dict]) -> dict:
    f = _case(by_id, "GIBSON_FMC_2030I")
    if f["reparations_cents"] + f["interest_cents"] != f["total_award_cents"]:
        raise AssertionError("FMC reparations and interest must not be conflated")
    return {"published_award_cents": f["total_award_cents"],
            "published_reparations_cents": f["reparations_cents"],
            "published_interest_cents": f["interest_cents"],
            "independently_verified_customer_invoice_overcharge_cents": None}


def tesoro_study_quote(by_id: dict[str, dict], *, miles: int,
                       barrels: int, prior_month_barrels: int) -> int:
    """Pure synthetic price exercise; NOT an entitlement or customer invoice."""
    f = _case(by_id, "TESORO_2011_TRUCKING")
    if type(miles) is not int or type(barrels) is not int or type(prior_month_barrels) is not int:
        raise ValueError("bounded integer inputs only")
    if not 0 < barrels <= 1_000_000 or not 0 <= prior_month_barrels <= 20_000_000:
        raise ValueError("invalid hypothetical barrels")
    if miles == f["ambiguous_example_miles"]:
        raise ValueError("overlapping published mileage bands need authority review")
    if not f["mile_band_lower_exclusive"] < miles <= f["mile_band_upper_inclusive"]:
        raise ValueError("published rate not established for this synthetic mileage")
    available = max(0, f["dispatch_first_threshold_barrels"] - prior_month_barrels)
    first = min(barrels, available)
    excess = barrels - first
    return (barrels * f["mileage_rate_cents_per_barrel"]
            + first * f["dispatch_first_cents_per_barrel"]
            + excess * f["dispatch_excess_cents_per_barrel"])


def marine_study_quote(by_id: dict[str, dict], *, equipment: str, days: int) -> int:
    """Only the published per-day anchor; excludes other billable components."""
    f = _case(by_id, "MARATHON_2026_MARINE")
    mapping = {"C2": f["day_rate_c2_barge_cents"],
               "H3": f["day_rate_h3_barge_cents"],
               "B1": f["day_rate_b1_boat_cents"]}
    if equipment not in mapping or type(days) is not int or not 1 <= days <= 365:
        raise ValueError("unsupported equipment or study duration")
    return mapping[equipment] * days


def native_engine_invoice_hold(by_id: dict[str, dict], case_id: str) -> dict:
    """Exercise production canonical/rating/evidence modules with fabricated IDs."""
    if case_id not in {"BIG_G_2026_FACE", "PYLE_2021_FACE"}:
        raise ValueError("only public numerical faces enter this synthetic probe")
    f = _case(by_id, case_id)
    charges = [
        ChargeLine("SYN-LINEHAUL", "TRANSPORTATION", f["linehaul_cents"]),
        ChargeLine("SYN-FUEL", "FUEL", f["fuel_cents"]),
    ]
    if "liftgate_cents" in f:
        charges.append(ChargeLine("SYN-LIFTGATE", "LIFTGATE", f["liftgate_cents"]))
    synthetic_sha = sha256(("FABRICATED-STUDY-NOT-ORIGINAL-" + case_id).encode()).hexdigest()
    record = build_record(
        buyer_id="SYNTHETIC-BUYER", business_unit="NONCUSTOMER-STUDY",
        invoice_id="SYNTHETIC-INVOICE-" + case_id,
        invoice_date=f["invoice_date"], customer_id="SYNTHETIC-BUYER",
        currency="USD", shipment=ShipmentFacts(
            shipment_id="SYNTHETIC-SHIPMENT-" + case_id,
            carrier_id="SYNTHETIC-CARRIER", mode=f["mode"],
            service_date=f["shipment_date"], origin_postal="SYN-ORIGIN",
            destination_postal="SYN-DESTINATION", actual_weight_grams=1000,
            package_count=1,
        ),
        charges=tuple(charges),
        sources=(SourceArtifact(
            "SYNTHETIC-NUMERIC-STUDY", "NOT_AN_ORIGINAL_INVOICE",
            synthetic_sha, "2026-10-22T00:00:00.000000Z", "BATCH",
        ),),
    )
    book = AuthorityBook(())
    rated = rate_record(record, book)
    strict = review_freight_rate(record, book)
    if (rated.status != REVIEW_REQUIRED or rated.expected_total_cents is not None
            or rated.variance_cents is not None or
            strict.status != REVIEW_REQUIRED or
            strict.externally_verified_freight_error_cents is not None or
            strict.externally_verified_cash_recovered_cents != 0 or
            strict.independent_accuracy_scored):
        raise AssertionError("public numerical face improperly became a recovery claim")
    if not {"INDEPENDENT_SHIPMENT_DOCUMENT_MISSING",
            "NO_EFFECTIVE_SHIPMENT_RATE_AUTHORITY"}.issubset(set(strict.blockers)):
        raise AssertionError("freight evidence hold unexpectedly removed")
    return {"rated_status": rated.status, "evidence_status": strict.status,
            "verified_new_recovery_cents": strict.externally_verified_cash_recovered_cents}


def aggregate_receipt() -> dict:
    by_id = validate_manifest(load_manifest())
    pyle = pyle_face_arithmetic(by_id)
    big_g = big_g_face_arithmetic(by_id)
    evergreen = evergreen_reference(by_id)
    gibson = gibson_reference(by_id)
    if _case(by_id, "BAKERLY_SEAFRIGO_FMC")["disposition"] != "SHIPPING_ACT_CLAIMS_DISMISSED":
        raise AssertionError("legal negative control lost")
    if tesoro_study_quote(by_id, miles=45, barrels=100, prior_month_barrels=699950) != 29750:
        raise AssertionError("Tesoro threshold math changed")
    if marine_study_quote(by_id, equipment="C2", days=3) != 301800:
        raise AssertionError("Marathon marine rate arithmetic changed")
    probes = {key: native_engine_invoice_hold(by_id, key) for key in (
        "BIG_G_2026_FACE", "PYLE_2021_FACE")}
    return {
        "pack_version": "1.0.0",
        "fixture_metadata_sha256_not_original_document": fixture_sha256(),
        "public_real_world_source_leads": len(by_id),
        "categories": dict(sorted(Counter(row["category"] for row in by_id.values()).items())),
        "invoice_face_checks": {"PYLE": pyle, "BIG_G": big_g},
        "official_adjudication_reference_cents": {
            "EVERGREEN_DISPUTED": evergreen["adjudicated_case_dispute_cents"],
            "GIBSON_AWARD_INCLUDING_INTEREST": gibson["published_award_cents"],
        },
        "native_engine_invoice_probes": probes,
        "original_documents_ingested": 0, "verified_new_customer_overcharge_cents": None,
        "verified_new_customer_recovery_cents": 0, "billable_fees_cents": 0,
        "blind_real_precision": None, "blind_real_recall": None,
        "commercial_release_approved": False,
    }


if __name__ == "__main__":
    print(json.dumps(aggregate_receipt(), indent=2, sort_keys=True))
