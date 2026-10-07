import pytest

from freight.enterprise_adapters import (
    SFTPManifestEntry,
    X12FieldRef,
    X12InvoiceProfile,
    canonical_record_from_api,
    parse_x12,
    project_x12_invoice,
    verify_sftp_manifest,
)
from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.contracts import canonical_hash
from freight.incumbent_challenge import (
    ChallengeCandidate,
    IncumbentMatter,
    challenge_incumbent,
    freeze_incumbent_snapshot,
)


def test_incumbent_challenge_separates_known_and_net_new():
    snapshot = freeze_incumbent_snapshot(
        buyer_id="B1",
        business_unit="BU1",
        population_hash="p" * 64,
        source_hash="s" * 64,
        matters=(
            IncumbentMatter("M1", "INV1|SHIP1|FUEL", "FINDING", 500, "a" * 64),
            IncumbentMatter("M2", "INV2|SHIP2|LIFTGATE", "AUTOMATIC_CREDIT", 200, "b" * 64),
        ),
    )
    batch = challenge_incumbent(
        snapshot,
        (
            ChallengeCandidate("C1", "INV1|SHIP1|FUEL", "r1", "FUEL", 1500, 1000, 990000),
            ChallengeCandidate("C2", "INV3|SHIP3|DETENTION", "r2", "DETENTION", 4000, 1000, 900000),
        ),
    )
    states = {x.candidate_id: x.attribution_state for x in batch.dispositions}
    assert states == {"C1": "INCUMBENT_KNOWN", "C2": "CHALLENGER_ONLY"}
    assert batch.incumbent_known_cents == 500
    assert batch.challenger_only_cents == 3000


def test_incumbent_challenge_fails_duplicate_economic_identity_to_review():
    snapshot = freeze_incumbent_snapshot(
        buyer_id="B1",
        business_unit="BU1",
        population_hash="p" * 64,
        source_hash="s" * 64,
        matters=(),
    )
    batch = challenge_incumbent(
        snapshot,
        (
            ChallengeCandidate("C1", "INV1|SHIP1|FUEL", "r1", "FUEL", 1500, 1000, 990000),
            ChallengeCandidate("C2", "INV1|SHIP1|FUEL", "r2", "FUEL", 1500, 1000, 990000),
        ),
    )
    assert all(x.attribution_state == "REVIEW" for x in batch.dispositions)
    assert all("DUPLICATE_CHALLENGER_ECONOMIC_KEY" in x.blocker_codes for x in batch.dispositions)
    assert batch.challenger_only_cents == 0


def test_api_adapter_builds_canonical_record():
    payload = {
        "buyer_id": "B1",
        "business_unit": "BU1",
        "invoice_id": "INV1",
        "invoice_date": "2026-10-01",
        "customer_id": "CUST1",
        "currency": "USD",
        "shipment": {
            "shipment_id": "SHIP1",
            "carrier_id": "CAR1",
            "mode": "PARCEL",
            "service_date": "2026-09-30",
            "origin_postal": "17901",
            "destination_postal": "21224",
            "actual_weight_grams": 1000,
            "package_count": 1,
            "zone": "2",
        },
        "charges": [
            {"charge_id": "L1", "charge_code": "TRANSPORTATION", "billed_cents": 1200}
        ],
        "sources": [
            {
                "source_id": "SRC1",
                "kind": "API_INVOICE",
                "sha256": "a" * 64,
                "observed_at": "2026-10-06T12:00:00.000000Z",
                "transport": "API",
            }
        ],
    }
    record = canonical_record_from_api(payload)
    assert record.record_hash
    assert record.billed_total_cents == 1200
    assert record.shipment.mode == "PARCEL"


def test_sftp_manifest_requires_exact_accepted_receipts():
    data = b"a,b\n1,2\n"
    receipt = ingest_bytes(IngressEnvelope("I1", "B1", "BU1", "SFTP", "invoice.csv"), data)
    verified = verify_sftp_manifest(
        (SFTPManifestEntry("invoice.csv", receipt.file_sha256, receipt.size_bytes),),
        (receipt,),
    )
    assert verified.status == "VERIFIED"
    assert verified.accepted_count == 1

    mismatched = verify_sftp_manifest(
        (SFTPManifestEntry("invoice.csv", "f" * 64, receipt.size_bytes),),
        (receipt,),
    )
    assert mismatched.status == "REVIEW_REQUIRED"
    assert mismatched.mismatched_filenames == ("invoice.csv",)


def test_x12_adapter_uses_explicit_profile_not_hidden_semantics():
    text = "ISA*00*          *00*          *ZZ*SENDER*ZZ*RECEIVER*261006*1200*U*00501*1*0*T*:~ST*210*0001~B3*INV-9*SHIP-4*PP*20261001*1234.56~N1*CA*CARRIER-X~SE*4*0001~"
    document = parse_x12(text)
    profile = X12InvoiceProfile(
        invoice_id=X12FieldRef("B3", 1, 1),
        shipment_id=X12FieldRef("B3", 1, 2),
        invoice_date=X12FieldRef("B3", 1, 4),
        net_amount=X12FieldRef("B3", 1, 5),
        carrier_id=X12FieldRef("N1", 1, 2),
    )
    projection = project_x12_invoice(document, profile)
    assert projection.invoice_id == "INV-9"
    assert projection.shipment_id == "SHIP-4"
    assert projection.invoice_date == "20261001"
    assert projection.net_amount_cents == 123456
    assert projection.carrier_id == "CARRIER-X"


def test_x12_wrong_transaction_set_fails_closed():
    with pytest.raises(ValueError, match="unexpected X12 transaction set"):
        parse_x12("ST*214*0001~SE*2*0001~")


def test_challenge_disposition_hash_is_import_verifiable():
    snapshot = freeze_incumbent_snapshot(
        buyer_id="B1",
        business_unit="BU1",
        population_hash="p" * 64,
        source_hash="s" * 64,
        matters=(),
    )
    candidate = ChallengeCandidate(
        "C1",
        "INV9|SHIP9|DETENTION",
        "r" * 64,
        "DETENTION",
        5000,
        2000,
        950000,
        evidence_hashes=("e" * 64,),
    )
    batch = challenge_incumbent(snapshot, (candidate,))
    item = batch.dispositions[0]
    body = {
        "schema": 1,
        "snapshot_hash": snapshot.snapshot_hash,
        "candidate_id": candidate.candidate_id,
        "economic_key": candidate.economic_key,
        "record_hash": candidate.record_hash,
        "category": candidate.category,
        "billed_cents": candidate.billed_cents,
        "expected_cents": candidate.expected_cents,
        "confidence_ppm": candidate.confidence_ppm,
        "evidence_hashes": candidate.evidence_hashes,
        "attribution_state": item.attribution_state,
        "candidate_variance_cents": item.candidate_variance_cents,
        "net_new_candidate_cents": item.net_new_candidate_cents,
        "matched_incumbent_matter_ids": item.matched_incumbent_matter_ids,
        "blocker_codes": item.blocker_codes,
    }
    assert item.disposition_hash == canonical_hash(body)
