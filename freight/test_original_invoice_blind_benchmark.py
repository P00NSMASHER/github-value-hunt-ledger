"""Adversarial, offline tests: real source checks and cryptographic trust are distinct."""
from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from freight.freight_evidence_chain_readiness import (
    EXPECTED_FACE_COUNTS, SOURCE_FACE_CATALOG_HASH,
)
from freight.real_document_lab import FROZEN_DOCUMENT_SHA256
from freight.original_invoice_blind_benchmark import (
    BenchmarkError, SCOPE, baseline_receipt, build_private_population, canonical,
    score_private_population, sha, verify_population, _save_new_private,
)

SECRET = b"offline-only-test-secret-32-characters-minimum"
T0 = "2026-10-29T08:00:00Z"
T1 = "2026-10-29T08:30:00Z"
T2 = "2026-10-29T09:00:00Z"
T3 = "2026-10-29T09:30:00Z"


def original_aggregate_lab():
    freight = {}
    for issuer, count in EXPECTED_FACE_COUNTS.items():
        freight[issuer] = {
            "sha256": FROZEN_DOCUMENT_SHA256[issuer],
            "source_face_catalog_sha256": SOURCE_FACE_CATALOG_HASH[issuer],
            "frozen_original_sha256_verified": True,
            "distinct_invoice_face_ids": count,
            "invoice_face_amounts_extracted": count,
            "invoice_face_anchor_verification": {
                "checks": 5 if issuer == "globaltranz" else 10,
                "passed": 5 if issuer == "globaltranz" else 10,
                "failed": 0,
            },
            "validated_overcharge_cents": 0, "realized_recovery_cents": 0,
        }
    freight["globaltranz"]["original_invoice_line_amount_reconciliation"] = {
        "invoice_face_exact_line_sum": 100,
    }
    return {
        "production_release_approved": False,
        "commercial_reuse_validated": False,
        "freight_original_document_benchmark": freight,
        "blinded_freight_error_evaluation": {
            "unknown_cases_preserved": 110, "total_eligible_scored": 0,
            "precision": None, "recall": None,
        },
    }


def toy_population(*, count_gt=2, count_abf=1):
    source = {}
    for issuer, count in (("globaltranz", count_gt), ("arcbest", count_abf)):
        source[issuer] = {
            "sha256": FROZEN_DOCUMENT_SHA256[issuer],
            "catalog_sha256": SOURCE_FACE_CATALOG_HASH[issuer],
            "faces": [
                {"number": "DEMO-%s-%s" % (issuer, i), "page": i+4,
                 "cents": 10000 + i*2000, "invoice_date": "2025-04-05",
                 "shipment_date": "2025-04-02", "mode": "LTL"}
                for i in range(count)
            ],
        }
    return build_private_population(
        secret=SECRET, sources=source, frozen_at=T0, synthetic=True)


def identities():
    keys = {n: Ed25519PrivateKey.generate() for n in
            ("operator", "truth_owner", "reviewer_a", "reviewer_b")}
    trust = {
        role: base64.b64encode(key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode()
        for role, key in keys.items()
    }
    return keys, trust


def signed(body, keys, *roles):
    return {"body": body, "signatures": {
        role: base64.b64encode(keys[role].sign(canonical(body))).decode()
        for role in roles
    }}


def evidence_files(tmp_path: Path, unique="0"):
    result = {}
    for role in ("rate", "shipment", "payment", "adjudication"):
        p = tmp_path / ("independent-%s-%s.txt" % (role, unique))
        payload = ("%s-%s: controlled fake original document bytes" % (role, unique)).encode()
        p.write_bytes(payload)
        result[role] = {"sha256": sha(payload), "path": str(p),
                        "issuer": "TEST_EXTERNAL_%s" % role.upper(),
                        "source_locator": "test-document-line:%s:%s" % (role, unique)}
    return result


def packets(population, keys, tmp_path, *, labels=None, predictions=None):
    golds, models = [], []
    for index, c in enumerate(population["casebook"]):
        label = labels[index] if labels else "UNRESOLVED"
        pred = predictions[index] if predictions else "REVIEW"
        golds.append({
            "case_id": c["case_id"], "label": label,
            "source_pdf_sha256": c["source_pdf_sha256"],
            "original_invoice_total_cents": c["invoice_total_cents"],
            "variance_cents": 100 if label == "POSITIVE" else 0,
            "reviewer_a_label": label if label != "UNRESOLVED" else None,
            "reviewer_b_label": label if label != "UNRESOLVED" else None,
            "adjudication_note": None,
            "artifacts": evidence_files(tmp_path, str(index))
            if label != "UNRESOLVED" else {},
        })
        models.append({
            "case_id": c["case_id"], "label": pred,
            "variance_cents": 100 if pred == "POSITIVE" else (
                0 if pred == "NEGATIVE" else None),
            "model_output_sha256": sha(("test-model-%d" % index).encode()),
        })
    pred_body = {
        "population_sha256": population["population_sha256"],
        "operator_id": "test_operator", "frozen_at": T1,
        "cases": models,
    }
    truth_body = {
        "population_sha256": population["population_sha256"],
        "truth_owner_id": "test_truth", "reviewer_a_id": "test_reviewer_a",
        "reviewer_b_id": "test_reviewer_b", "frozen_at": T2,
        "cases": golds,
    }
    return signed(pred_body, keys, "operator"), signed(
        truth_body, keys, "truth_owner", "reviewer_a", "reviewer_b")


def score(pop, model, truth, keys):
    return score_private_population(pop, SECRET, model, truth, keys, T3)


def test_source_census_only_has_no_freight_accuracy_labels():
    report = baseline_receipt(original_aggregate_lab())
    assert report["source_pdfs_pinned"] == 2
    assert report["original_invoice_faces"] == 110
    assert report["original_face_arithmetic_verified"] == 100
    assert report["unresolved_unscored_cases"] == 110
    assert report["precision"] is None and report["recall"] is None
    assert report["commercial_release_approved"] is False
    assert report["billable_fees_cents"] == 0
    assert len(report["receipt_sha256"]) == 64
    # Neither invoice IDs nor originals may appear in safe aggregate output.
    assert "invoice_number" not in json.dumps(report)


@pytest.mark.parametrize("mutate", [
    lambda x: x["freight_original_document_benchmark"]["globaltranz"].update(
        {"distinct_invoice_face_ids": 99}),
    lambda x: x["freight_original_document_benchmark"]["arcbest"].update(
        {"sha256": "1"*64}),
    lambda x: x["freight_original_document_benchmark"]["arcbest"][
        "invoice_face_anchor_verification"].update({"failed": 1}),
    lambda x: x["blinded_freight_error_evaluation"].update({"precision": 1.0}),
    lambda x: x["freight_original_document_benchmark"]["globaltranz"].update(
        {"validated_overcharge_cents": 100}),
])
def test_source_census_regressions_fail_closed(mutate):
    report = original_aggregate_lab()
    mutate(report)
    with pytest.raises(BenchmarkError):
        baseline_receipt(report)


def test_private_case_ids_bind_pdf_page_amount_and_original_reference():
    pop = toy_population()
    verify_population(pop, SECRET)
    assert len(pop["casebook"]) == 3
    assert len({c["case_id"] for c in pop["casebook"]}) == 3
    assert pop["scope"] == "SYNTHETIC_REHEARSAL_ONLY"
    assert all(len(c["case_id"]) == 64 for c in pop["casebook"])
    assert all("DEMO" not in c["case_id"] for c in pop["casebook"])
    changed = deepcopy(pop)
    changed["casebook"][0]["invoice_total_cents"] += 1
    with pytest.raises(BenchmarkError, match="MAC_MISMATCH"):
        verify_population(changed, SECRET)


def test_synthetic_cannot_be_marked_real_merely_by_swapping_flags():
    pop = toy_population()
    pop["scope"] = SCOPE
    pop["original_byte_checks_executed"] = True
    with pytest.raises(BenchmarkError, match="MAC_MISMATCH"):
        verify_population(pop, SECRET)


def test_original_corpus_will_require_all_110_faces():
    fake = {}
    for issuer in EXPECTED_FACE_COUNTS:
        fake[issuer] = {
            "sha256": FROZEN_DOCUMENT_SHA256[issuer],
            "catalog_sha256": SOURCE_FACE_CATALOG_HASH[issuer],
            "faces": [{"number": "FAKE", "page": 1, "cents": 100}],
        }
    with pytest.raises(BenchmarkError, match="ORIGINAL_FACE_COUNT_DRIFT"):
        build_private_population(
            secret=SECRET, sources=fake, frozen_at=T0, synthetic=False)


def test_missing_independent_truth_is_110_percent_not_accuracy(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path)
    receipt = score(pop, model, truth, trust)
    assert receipt["unresolved_unknown_case_count"] == 3
    assert receipt["precision"] is None and receipt["recall_including_review_abstentions"] is None
    assert receipt["commercial_release_approved"] is False
    assert receipt["existing_audit_acceptance_v2_executed"] is False
    assert receipt["method_status"] == "SYNTHETIC_REHEARSAL_NOT_REAL_ACCURACY"


def test_signed_synthetic_reference_confusion_matrix_and_abstentions(tmp_path):
    pop = toy_population(count_gt=3, count_abf=2)
    keys, trust = identities()
    model, truth = packets(
        pop, keys, tmp_path,
        labels=["POSITIVE", "NEGATIVE", "POSITIVE", "NEGATIVE", "UNRESOLVED"],
        predictions=["POSITIVE", "POSITIVE", "REVIEW", "NEGATIVE", "REVIEW"],
    )
    receipt = score(pop, model, truth, trust)
    assert receipt["true_positive"] == 1
    assert receipt["false_positive"] == 1
    assert receipt["true_negative"] == 1
    assert receipt["false_negative"] == 0
    assert receipt["positive_review_abstentions"] == 1
    assert receipt["unresolved_unknown_case_count"] == 1
    assert receipt["precision"] == 0.5
    assert receipt["recall_including_review_abstentions"] == 0.5
    assert receipt["precision_wilson_95"]["lower"] < 0.5
    assert receipt["false_positive_dollars_cents"] == 100
    assert receipt["billable_fees_cents"] == 0
    assert receipt["commercial_release_approved"] is False


def test_signed_attack_rejected_even_if_checksum_changed(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path)
    attacks = []
    x = deepcopy(truth)
    x["body"]["cases"][0]["label"] = "POSITIVE"
    x["body"]["cases"][0]["variance_cents"] = 99
    attacks.append((model, x, trust))
    x = deepcopy(model)
    x["body"]["cases"][0]["label"] = "POSITIVE"
    x["body"]["cases"][0]["variance_cents"] = 999999
    attacks.append((x, truth, trust))
    x = deepcopy(trust)
    x["reviewer_b"] = x["reviewer_a"]
    attacks.append((model, truth, x))
    for pm, pt, tk in attacks:
        with pytest.raises(BenchmarkError):
            score(pop, pm, pt, tk)


def test_incomplete_proof_bytes_and_historic_no_link_are_not_labels(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(
        pop, keys, tmp_path, labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    proof = truth["body"]["cases"][0]["artifacts"]
    Path(proof["rate"]["path"]).write_bytes(b"CHANGED")
    # Even newly signed tampering cannot make an incorrect original source hash valid.
    signed_truth = signed(truth["body"], keys,
                          "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="HASH_MISMATCH"):
        score(pop, model, signed_truth, trust)


def test_auto_positive_on_unresolved_is_reported_as_unsafe(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path,
                           predictions=["POSITIVE", "NEGATIVE", "REVIEW"])
    receipt = score(pop, model, truth, trust)
    assert receipt["unsupported_automatic_calls_on_unresolved"] == 2
    assert receipt["precision"] is None
    assert receipt["commercial_release_approved"] is False


def test_private_population_file_refuses_repo_and_permissions(tmp_path):
    pop = toy_population()
    path = tmp_path / "private-population.json"
    _save_new_private(path, pop)
    assert path.exists()
    assert (path.stat().st_mode & 0o077) == 0
    with pytest.raises(FileExistsError):
        _save_new_private(path, pop)
    with pytest.raises(BenchmarkError, match="OUTSIDE_REPOSITORY"):
        _save_new_private(
            Path(__file__).parent / "MUST_NOT_WRITE_SOURCE_MANIFEST.json", pop)


def test_trust_packet_cannot_assign_positive_against_both_negative_reviews(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(
        pop, keys, tmp_path, labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    truth["body"]["cases"][0]["reviewer_a_label"] = "NEGATIVE"
    truth["body"]["cases"][0]["reviewer_b_label"] = "NEGATIVE"
    truth = signed(truth["body"], keys,
                   "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="REVIEWER_CONSENSUS"):
        score(pop, model, truth, trust)


def test_reviewed_case_must_match_original_invoice_money(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path,
                           labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    truth["body"]["cases"][0]["original_invoice_total_cents"] += 1
    truth = signed(truth["body"], keys,
                   "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="ORIGINAL_FACE_MONEY"):
        score(pop, model, truth, trust)


def test_same_bank_payment_line_cannot_count_for_two_cases(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path,
                           labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    first = truth["body"]["cases"][0]["artifacts"]["payment"]
    second = truth["body"]["cases"][1]["artifacts"]["payment"]
    second.update(first)
    truth = signed(truth["body"], keys,
                   "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="DUPLICATE_INDEPENDENT"):
        score(pop, model, truth, trust)


def test_same_shipment_proof_line_cannot_count_for_two_cases(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path,
                           labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    first = truth["body"]["cases"][0]["artifacts"]["shipment"]
    second = truth["body"]["cases"][1]["artifacts"]["shipment"]
    second.update(first)
    truth = signed(truth["body"], keys,
                   "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="DUPLICATE_INDEPENDENT"):
        score(pop, model, truth, trust)

def test_duplicate_shipment_locator_whitespace_cannot_bypass_line_identity(tmp_path):
    pop = toy_population()
    keys, trust = identities()
    model, truth = packets(pop, keys, tmp_path,
                           labels=["POSITIVE", "NEGATIVE", "UNRESOLVED"])
    first = truth["body"]["cases"][0]["artifacts"]["shipment"]
    second = truth["body"]["cases"][1]["artifacts"]["shipment"]
    second.update(first)
    second["source_locator"] = "  %s  " % first["source_locator"]
    truth = signed(truth["body"], keys,
                   "truth_owner", "reviewer_a", "reviewer_b")
    with pytest.raises(BenchmarkError, match="DUPLICATE_INDEPENDENT"):
        score(pop, model, truth, trust)

