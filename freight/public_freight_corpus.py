"""RETALLY source-rights gated, privacy-safe public freight research.

Contains only public locators, curated non-identifying monetary facts and
SYNTHETIC study shipments. No original third-party files, bank records,
customer identities, private tariffs, documents, or recovered funds.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from urllib.parse import urlsplit

from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.scoped_reconciliation import ScopedTxn, reconcile_scoped
from recoveryworks.reconciliation_kernel import ReconTxn


@dataclass(frozen=True)
class PublicSource:
    key: str
    publisher: str
    url: str
    permission_url: str | None
    permission: str
    evidence_type: str
    locator: str
    original_bytes_sha256: None = None
    verified_bank_source: bool = False
    commercial_recovery_authorized: bool = False

    @property
    def url_sha256(self) -> str:
        # URL identity only, absolutely NOT a digest of the original file.
        return sha256(self.url.encode()).hexdigest()


SEC_RIGHTS = "https://www.sec.gov/about/webmaster-frequently-asked-questions"
GAO_RIGHTS = "https://www.gao.gov/copyright"
OD_RIGHTS = "https://www.odfl.com/us/en/terms-and-conditions.html"

SOURCES = (
    PublicSource(
        "SEC_BULK_2007", "SEC EDGAR",
        "https://www.sec.gov/Archives/edgar/data/1337226/000092290707000474/form8kexh101_072507.htm",
        SEC_RIGHTS, "OFFICIAL_REUSE_ALLOWED", "HISTORICAL_RATE",
        "Exhibit A, $0.01299 per unloaded gallon, stepped diesel surcharge",
    ),
    PublicSource(
        "SEC_INTERMODAL_2013", "SEC EDGAR",
        "https://www.sec.gov/Archives/edgar/data/739878/000119312514144221/d658018dex1063.htm",
        SEC_RIGHTS, "OFFICIAL_REUSE_ALLOWED", "HISTORICAL_RATE",
        "Schedule 2.1 page 43; two fuel-inclusive intermodal lanes",
    ),
    PublicSource(
        "GAO_B160344", "GAO",
        "https://www.gao.gov/products/b-160344", GAO_RIGHTS,
        "OFFICIAL_REUSE_ALLOWED", "HISTORICAL_ADJUDICATION",
        "1967 decision: $275.17 paid, $139.29 allowed, $135.88 deducted",
    ),
    PublicSource(
        "OD_FUEL_2026", "Old Dominion",
        "https://www.odfl.com/us/en/resources/fuel-surcharge.html",
        OD_RIGHTS, "INFORMATIONAL_ONLY", "TARIFF_HISTORY",
        "Weekly 2026 table; NOT copied or licensed into commercial corpus",
    ),
    PublicSource(
        "KENTUCKY_PSC_2024", "Kentucky PSC",
        "https://psc.ky.gov/Case/ViewCaseFilings/2025-00354",
        None, "RIGHTS_NOT_ESTABLISHED", "ORIGINAL_INVOICE_DOCKET",
        "Exhibit PSC 1-13 Part 8(b), pp. 2323/2326; no original document saved",
    ),
)
BY_KEY = {s.key: s for s in SOURCES}

# These are published public contractual prices, NOT proven governing on any
# synthetic/test shipment. Original agreements and amendments are not ingested.
SEC_LANES = {
    "KENTWOOD_CHINO": ("KENTWOOD_MI", "CHINO_CA", 242500),
    "CRANBURY_CHINO": ("CRANBURY_NJ", "CHINO_CA", 230000),
}


def source(key: str) -> PublicSource:
    if key not in BY_KEY:
        raise ValueError("not in official, closed source allowlist")
    return BY_KEY[key]


def require_reuse(key: str, *, import_original: bool = False,
                  commercial_distribution: bool = False) -> None:
    item = source(key)
    # Even reusable SEC/GAO publication rights do not grant customer rights or
    # authorize putting real invoices into the public repository.
    if import_original:
        raise PermissionError("original documents require private authenticated source custody")
    if commercial_distribution:
        raise PermissionError("commercial customer reuse has not been authorized")
    if item.permission != "OFFICIAL_REUSE_ALLOWED":
        raise PermissionError("metadata-only source; additional rights required")


def catalog_sha256() -> str:
    if len(SOURCES) != 5 or len(BY_KEY) != 5:
        raise ValueError("source population or source identity changed")
    for s in SOURCES:
        u = urlsplit(s.url)
        if (u.scheme != "https" or u.hostname not in
            {"www.sec.gov", "www.gao.gov", "www.odfl.com", "psc.ky.gov"}
            or u.username or u.password or u.query or u.fragment
            or "@" in u.path or "%40" in u.path.lower()):
            raise ValueError("non-allowlisted URL or unsafe private filing locator")
        if (s.original_bytes_sha256 is not None or s.verified_bank_source
                or s.commercial_recovery_authorized):
            raise ValueError("public research cannot assert source-byte/bank/buyer proof")
    payload = [{**asdict(s), "url_sha256": s.url_sha256} for s in SOURCES]
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def to_cents(value: Decimal) -> int:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("money must be a finite nonnegative Decimal")
    cents = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents > 2**63 - 1:
        raise ValueError("cents overflow")
    return cents


def historical_gao_arithmetic() -> dict:
    require_reuse("GAO_B160344")
    claimed = to_cents(Decimal(1485) * Decimal("18.53") / 100)
    allowed = to_cents(Decimal(1485) * Decimal("9.38") / 100)
    if (claimed, allowed, claimed - allowed) != (27517, 13929, 13588):
        raise AssertionError("published historical classification arithmetic mismatch")
    return {
        "claimed_cents": claimed, "allowed_cents": allowed,
        "historical_offset_cents": claimed - allowed,
        "retally_recovered_cents": 0,
        "modern_invoice_adjudicated": False,
    }


def historical_bulk_probe(gallons: int, fuel_step: str = "0") -> dict:
    require_reuse("SEC_BULK_2007")
    if type(gallons) is not int or not 1 <= gallons <= 1000000:
        raise ValueError("synthetic gallon quantity must be a bounded integer")
    if fuel_step not in {"0", "0.0003", "0.0006", "0.0009",
                         "0.0012", "0.0015", "0.0018"}:
        raise ValueError("unpublished fuel step")
    base = to_cents(Decimal("0.01299") * gallons)
    fuel = to_cents(Decimal(fuel_step) * gallons)
    return {"synthetic_gallons": gallons, "base_cents": base,
            "fuel_cents": fuel, "scenario_total_cents": base + fuel,
            "verified_new_recovery_cents": 0}


def intermodal_probe(*, lane: str, origin: str, destination: str,
                     service_date: str, billed_cents: int):
    """Call the actual rating and strict evidence engines, SYNTHETIC ONLY.

    Native intermodal terms have no lane keys. Match the exact published lane
    BEFORE using them; date is an isolated study fixture, not contract proof.
    """
    require_reuse("SEC_INTERMODAL_2013")
    if lane not in SEC_LANES:
        raise ValueError("unregistered lane")
    expected_origin, expected_destination, published_cents = SEC_LANES[lane]
    if (origin, destination) != (expected_origin, expected_destination):
        raise ValueError("lane mismatch; no cross-lane tariff application")
    if service_date != "2013-10-15":
        raise ValueError("outside bounded synthetic study date")
    if type(billed_cents) is not int or billed_cents <= 0:
        raise ValueError("positive synthetic invoice cents required")
    # Explicit fabricated *probe* source hash; NOT original SEC agreement SHA.
    synthetic_sha = sha256(b"SYNTHETIC-NOT-ORIGINAL-SEC-RATE-AND-SHIPMENT").hexdigest()
    shipment = ShipmentFacts(
        shipment_id="SYNTHETIC-" + lane, carrier_id="SYNTHETIC-CARRIER",
        mode="INTERMODAL", service_date=service_date,
        origin_postal="SYN-" + origin, destination_postal="SYN-" + destination,
        actual_weight_grams=1000, package_count=1,
    )
    record = build_record(
        buyer_id="SYNTHETIC-BUYER", business_unit="ISOLATED-PUBLIC-TEST",
        invoice_id="SYNTHETIC-INVOICE-" + lane, invoice_date=service_date,
        customer_id="SYNTHETIC-BUYER", currency="USD", shipment=shipment,
        charges=(ChargeLine("SYN-LINE", "TRANSPORTATION", billed_cents),),
        sources=(SourceArtifact(
            "SYNTHETIC-STUDY-ONLY", "NOT_AN_ORIGINAL_INVOICE",
            synthetic_sha, "2026-10-22T00:00:00.000000Z", "BATCH",
        ),),
    )
    compiled = compile_authority({
        "authority_id": "SYNTHETIC-PRICE-MODEL-" + lane,
        "buyer_id": record.buyer_id, "business_unit": record.business_unit,
        "customer_id": record.customer_id,
        "carrier_id": shipment.carrier_id, "currency": "USD",
        "mode": "INTERMODAL", "effective_from": service_date,
        "effective_to": service_date,
        "terms": {"base_cents": published_cents, "per_mile_cents": 0,
                  "fuel_bps": 0, "chassis_per_day_cents": 0,
                  "accessorials": {}},
    }, source_sha256=synthetic_sha, verified_controlling_authority=False)
    book = AuthorityBook((compiled,))
    modeled = rate_record(record, book)
    strict = review_freight_rate(record, book)
    if (modeled.status != REVIEW_REQUIRED or
        modeled.expected_total_cents != published_cents or
        strict.status != REVIEW_REQUIRED or
        strict.externally_verified_freight_error_cents is not None or
        strict.externally_verified_cash_recovered_cents != 0):
        raise AssertionError("hypothetical rate incorrectly promoted to authority")
    if not any(x.code == "FUEL" and x.expected_cents == 0
               for x in modeled.components):
        raise AssertionError("fuel-inclusive schedule must not add a fuel surcharge")
    return modeled, strict


def kentucky_numeric_fact_and_reconciliation_hold() -> dict:
    """No PSC PDF read. Only published arithmetic, fictitious IDs and no bank."""
    # 2024 freight line $184.00; associated EXPENSE 1.09 x = $200.56;
    # the difference is NOT a carrier overcharge or bank-settled receipt.
    base = 18400
    expense = to_cents(Decimal("184.00") * Decimal("1.09"))
    if expense != 20056:
        raise AssertionError("public numerical anchor altered")
    original = ScopedTxn(
        ReconTxn("SYNTHETIC-INVOICE", "184.00", "2024-03-09", "USD",
                 "SYNTHETIC-REFERENCE"),
        buyer_id="SYNTHETIC-BUYER", business_unit="ISOLATED-STUDY",
        counterparty_id="SYNTHETIC-CARRIER", origin="ORIGINAL_INVOICE",
    )
    # Crucially, the publisher's expense figure is NOT fed to the bank side.
    matched = reconcile_scoped((original,), ())
    if (matched.matched_internal or matched.proven_cleared_payment_count
            or matched.independent_payment_accuracy is not None
            or matched.unmatched_internal != 1):
        raise AssertionError("public expense mistaken for independent bank payment")
    return {
        "original_pdf_ingested": False, "published_charge_cents": base,
        "published_expense_cents": expense,
        "expense_markup_cents_not_carrier_overcharge": expense - base,
        "bank_matches": 0, "verified_new_recovery_cents": 0,
    }


def aggregate_research_receipt() -> dict:
    checksum = catalog_sha256()
    historical = historical_gao_arithmetic()
    bulk = historical_bulk_probe(1000, "0.0003")
    ky = kentucky_numeric_fact_and_reconciliation_hold()
    lane_receipts = []
    for name, (origin, destination, amount) in SEC_LANES.items():
        rated, strict = intermodal_probe(
            lane=name, origin=origin, destination=destination,
            service_date="2013-10-15", billed_cents=amount)
        lane_receipts.append({
            "lane": name, "published_price_probe_cents": rated.expected_total_cents,
            "rated_state": rated.status, "evidence_state": strict.status,
            "verified_recovered_cents": strict.externally_verified_cash_recovered_cents,
        })
    return {
        "classification": "PUBLIC_NUMERIC_FACTS_AND_SYNTHETIC_ENGINE_TESTS_ONLY",
        "url_metadata_catalog_sha256": checksum,
        "source_leads": len(SOURCES), "real_source_fact_case_families": 5,
        "official_reusable_source_leads": 3, "rights_restricted_source_leads": 2,
        "intermodal_engine_probe_results": lane_receipts,
        "historical_gao_arithmetic_valid": historical["historical_offset_cents"] == 13588,
        "synthetic_bulk_scenario_total_cents": bulk["scenario_total_cents"],
        "kentucky_original_pdf_ingested": ky["original_pdf_ingested"],
        "source_document_byte_hashes_verified": 0,
        "actual_customer_documents_ingested": 0,
        "independently_adjudicated_new_freight_invoices": 0,
        "verified_new_customer_recovery_cents": 0,
        "billable_customer_fee_cents": 0,
        "real_precision": None, "real_recall": None,
    }


if __name__ == "__main__":
    print(json.dumps(aggregate_research_receipt(), sort_keys=True, indent=2))
