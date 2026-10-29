"""Private, source-bound blind benchmark bridge for the 110 original freight invoices.

No commercial truth is inferred from an invoice, its statement, a BOL copied in
the same PDF, or a historical GAO/FMC ruling about different invoices.

Only a separately trusted, signed evidence-review packet can produce
conditional accuracy metrics. Buyer approval and audit_acceptance v2 remain
separate launch gates. Source identifiers and originals NEVER go to Actions
logs, public fixtures, or a committed casebook.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any

from freight.audit_acceptance import _wilson
from freight.freight_evidence_chain_readiness import (
    EXPECTED_FACE_COUNTS, SOURCE_FACE_CATALOG_HASH,
)
from freight.real_document_lab import FROZEN_DOCUMENT_SHA256

SCHEMA_VERSION = 1
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_TYPES = {"POSITIVE", "NEGATIVE", "UNRESOLVED"}
PRED_TYPES = {"POSITIVE", "NEGATIVE", "REVIEW"}
ARTIFACTS = ("rate", "shipment", "payment", "adjudication")
# Neither public historical adjudication nor same-PDF statements qualify here.
SCOPE = "PUBLIC_ORIGINAL_INVOICE_CENSUS_RESEARCH_ONLY"
REPO_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkError(ValueError):
    """Fail-closed without including source invoice identifiers."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise BenchmarkError("INVALID_PROVENANCE_SHA256")
    return value


def _iso(value: Any) -> datetime:
    if not isinstance(value, str):
        raise BenchmarkError("FREEZE_TIME_MISSING")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkError("FREEZE_TIME_INVALID") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise BenchmarkError("FREEZE_TIME_NEEDS_TIMEZONE")
    return dt.astimezone(timezone.utc)


def _key(secret: bytes) -> bytes:
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise BenchmarkError("PRIVATE_HMAC_KEY_MUST_BE_AT_LEAST_32_BYTES")
    return secret


def _mac(secret: bytes, value: object) -> str:
    return hmac.new(_key(secret), canonical(value), hashlib.sha256).hexdigest()


def _private_path(path: str | Path) -> Path:
    p = Path(path).expanduser().resolve()
    if p == REPO_ROOT or REPO_ROOT in p.parents:
        raise BenchmarkError("PRIVATE_RECORDS_MUST_STAY_OUTSIDE_REPOSITORY")
    if p.is_symlink():
        raise BenchmarkError("SYMLINKED_EVIDENCE_FORBIDDEN")
    return p


def _save_new_private(path: str | Path, value: object) -> None:
    # Windows storage ACLs must be provisioned and verified by the operator's
    # private vault, not inferred from chmod. Never create unprotected files.
    if os.name != "posix":
        raise BenchmarkError("PRIVATE_VAULT_REQUIRED_ON_THIS_PLATFORM")
    target = _private_path(path)
    if not target.parent.exists() or not target.parent.is_dir():
        raise BenchmarkError("PRIVATE_OUTPUT_DIRECTORY_MISSING")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(canonical(value) + b"\n")
        if target.stat().st_mode & 0o077:
            raise BenchmarkError("PRIVATE_FILE_PERMISSIONS_NOT_RESTRICTED")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _expected_source(issuer: str, source_sha: str, catalog_sha: str) -> None:
    if issuer not in EXPECTED_FACE_COUNTS:
        raise BenchmarkError("UNEXPECTED_ORIGINAL_SOURCE")
    if (source_sha != FROZEN_DOCUMENT_SHA256[issuer]
            or catalog_sha != SOURCE_FACE_CATALOG_HASH[issuer]):
        raise BenchmarkError("ORIGINAL_SOURCE_OR_FACE_CATALOG_DRIFT")


def baseline_receipt(lab_report: dict) -> dict:
    """Aggregate-only proof of the original PDF census, NOT freight accuracy."""
    if not isinstance(lab_report, dict):
        raise BenchmarkError("LAB_REPORT_MISSING")
    if (lab_report.get("production_release_approved") is not False or
            lab_report.get("commercial_reuse_validated") is not False):
        raise BenchmarkError("LAB_SCOPE_CHANGED")
    freight = lab_report.get("freight_original_document_benchmark")
    if not isinstance(freight, dict) or set(freight) != set(EXPECTED_FACE_COUNTS):
        raise BenchmarkError("ORIGINAL_CENSUS_SOURCE_SET_CHANGED")
    for issuer, expected in EXPECTED_FACE_COUNTS.items():
        item = freight[issuer]
        if type(item) is not dict:
            raise BenchmarkError("ORIGINAL_CENSUS_ROW_INVALID")
        _expected_source(issuer, item.get("sha256"), item.get("source_face_catalog_sha256"))
        checks = item.get("invoice_face_anchor_verification", {})
        if (item.get("frozen_original_sha256_verified") is not True
                or type(item.get("distinct_invoice_face_ids")) is not int
                or item["distinct_invoice_face_ids"] != expected
                or item.get("invoice_face_amounts_extracted") != expected
                or checks.get("checks") != checks.get("passed")
                or checks.get("failed") != 0
                or not isinstance(checks.get("checks"), int)
                or checks.get("checks") < 1
                or item.get("validated_overcharge_cents") != 0
                or item.get("realized_recovery_cents") != 0):
            raise BenchmarkError("ORIGINAL_CENSUS_NOT_INDEPENDENTLY_READY")
    blind = lab_report.get("blinded_freight_error_evaluation")
    if (not isinstance(blind, dict) or
            blind.get("unknown_cases_preserved") != sum(EXPECTED_FACE_COUNTS.values()) or
            blind.get("total_eligible_scored") != 0 or
            blind.get("precision") is not None or
            blind.get("recall") is not None):
        raise BenchmarkError("UNVERIFIED_BENCHMARK_PROMOTION")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        # Hashes of original PDFs and source-face catalogs bind the published
        # aggregate without releasing page-level invoice IDs.
        "source_bindings": {
            name: {
                "source_pdf_sha256": FROZEN_DOCUMENT_SHA256[name],
                "source_face_catalog_sha256": SOURCE_FACE_CATALOG_HASH[name],
                "original_face_count": EXPECTED_FACE_COUNTS[name],
            }
            for name in sorted(EXPECTED_FACE_COUNTS)
        },
        "source_pdfs_pinned": len(EXPECTED_FACE_COUNTS),
        "original_invoice_faces": sum(EXPECTED_FACE_COUNTS.values()),
        "original_face_arithmetic_verified": freight["globaltranz"][
            "original_invoice_line_amount_reconciliation"].get(
                "invoice_face_exact_line_sum", 0),
        "independently_linked_rate_shipment_payment_adjudication_cases": 0,
        "unresolved_unscored_cases": sum(EXPECTED_FACE_COUNTS.values()),
        "precision": None, "recall": None, "false_positive_rate": None,
        "confidence_intervals": None,
        "blinded_independent_review_completed": False,
        "method_status": "SOURCE_CENSUS_PINNED_INDEPENDENT_TRUTH_NOT_ACQUIRED",
        "commercial_release_approved": False,
        "recovered_cash_cents": 0,
        "billable_fees_cents": 0,
    }
    # Do not serialize or expose individual invoice identities in receipts.
    if receipt["original_face_arithmetic_verified"] != 100:
        raise BenchmarkError("ORIGINAL_SIGNED_COMPONENT_RECONCILIATION_DRIFT")
    receipt["receipt_sha256"] = sha(canonical(receipt))
    return receipt


def build_private_population(*, secret: bytes, sources: dict,
                             frozen_at: str, synthetic: bool = False) -> dict:
    """Only the real private CLI may declare a verified original corpus.

    Tests can pass synthetic=True, but those manifests are forever marked
    SYNTHETIC and cannot be scored or promoted as original real-invoice data.
    """
    _key(secret)
    _iso(frozen_at)
    if set(sources) != set(EXPECTED_FACE_COUNTS):
        raise BenchmarkError("EXACT_TWO_SOURCE_POPULATION_REQUIRED")
    rows: list[dict] = []
    bindings: dict[str, dict] = {}
    seen_originals: set[tuple[str, str]] = set()
    seen_case_ids: set[str] = set()
    for issuer in sorted(EXPECTED_FACE_COUNTS):
        source = sources[issuer]
        original_sha = _exact_sha(source["sha256"])
        faces = source["faces"]
        if not synthetic:
            if len(faces) != EXPECTED_FACE_COUNTS[issuer]:
                raise BenchmarkError("ORIGINAL_FACE_COUNT_DRIFT")
            _expected_source(issuer, original_sha, source["catalog_sha256"])
        elif not faces:
            raise BenchmarkError("SYNTHETIC_FACE_SAMPLE_REQUIRED")
        seen = []
        for face in faces:
            number, page, cents = face["number"], face["page"], face["cents"]
            if (not isinstance(number, str) or not number.strip()
                    or not isinstance(page, int) or type(page) is bool or page < 1
                    or type(cents) is not int or not 0 <= cents <= 10**12):
                raise BenchmarkError("INVALID_SOURCE_FACE")
            identity = (issuer, number)
            if identity in seen_originals:
                raise BenchmarkError("DUPLICATE_ORIGINAL_FACE")
            seen_originals.add(identity)
            bare = {
                "issuer": issuer, "source_pdf_sha256": original_sha,
                "invoice_number": number, "source_page": page,
                "invoice_total_cents": cents,
                "invoice_date": face.get("invoice_date"),
                "shipment_date": face.get("shipment_date"),
                "mode": face.get("mode"),
            }
            uid = _mac(secret, {"case_namespace": "RETALLY-ORIGINAL-FACE-v1", **bare})
            if uid in seen_case_ids:
                raise BenchmarkError("DUPLICATE_BLINDED_CASE_ID")
            seen_case_ids.add(uid)
            rows.append({"case_id": uid, **bare})
            seen.append((number, page, cents))
        catalog = sha(canonical(sorted(seen)))
        if not synthetic and catalog != source["catalog_sha256"]:
            # Match original real_document_lab's serialized source-face layout,
            # including its ordering and separators.
            original_layout_hash = sha(json.dumps(
                sorted(seen), separators=(",", ":"), ensure_ascii=True,
            ).encode())
            if original_layout_hash != source["catalog_sha256"]:
                raise BenchmarkError("ORIGINAL_FACE_HASH_MISMATCH")
        bindings[issuer] = {
            "source_pdf_sha256": original_sha,
            "source_face_catalog_sha256": source["catalog_sha256"],
            "count": len(faces),
        }
    rows.sort(key=lambda row: row["case_id"])
    body = {
        "schema_version": SCHEMA_VERSION,
        "scope": "SYNTHETIC_REHEARSAL_ONLY" if synthetic else SCOPE,
        "original_byte_checks_executed": not synthetic,
        "population_frozen_at": frozen_at,
        "sources": bindings,
        "casebook": rows,
    }
    body["population_sha256"] = sha(canonical(body))
    return {**body, "population_hmac_sha256": _mac(secret, body)}


def collect_private_population(secret: bytes) -> dict:
    """Fresh source-byte and exact face checks in memory; no invoice logging."""
    from freight.real_document_lab import (
        ARCBEST_FACE_ANCHORS, DOCUMENTS, GLOBAL_FACE_ANCHORS,
        check_anchors, extract_faces, fetch_public, index_unique_invoice_faces,
        pdf_texts, require_frozen_source,
    )
    sources: dict[str, dict] = {}
    for issuer in sorted(EXPECTED_FACE_COUNTS):
        original = fetch_public(DOCUMENTS[issuer])
        source_sha = require_frozen_source("document", issuer, original)
        faces = extract_faces(issuer, pdf_texts(original))
        faces_by_id = index_unique_invoice_faces(faces, issuer)
        check = check_anchors(
            faces, GLOBAL_FACE_ANCHORS if issuer == "globaltranz"
            else ARCBEST_FACE_ANCHORS,
        )
        if (check["failed"] or check["passed"] != check["checks"]
                or len(faces_by_id) != EXPECTED_FACE_COUNTS[issuer]):
            raise BenchmarkError("ORIGINAL_ANCHORS_OR_POPULATION_CHANGED")
        seen = sorted((f.number, f.page, f.cents) for f in faces_by_id.values())
        source_catalog = sha(json.dumps(
            seen, separators=(",", ":"), ensure_ascii=True,
        ).encode())
        _expected_source(issuer, source_sha, source_catalog)
        sources[issuer] = {
            "sha256": source_sha, "catalog_sha256": source_catalog,
            "faces": [
                {"number": f.number, "page": f.page, "cents": f.cents,
                 "invoice_date": f.invoice_date, "shipment_date": f.shipment_date,
                 "mode": f.mode}
                for f in faces_by_id.values()
            ],
        }
    return build_private_population(
        secret=secret, sources=sources,
        frozen_at=datetime.now(timezone.utc).isoformat(), synthetic=False,
    )


def verify_population(population: dict, secret: bytes) -> None:
    if not isinstance(population, dict):
        raise BenchmarkError("PRIVATE_POPULATION_INVALID")
    body = {k: v for k, v in population.items() if k != "population_hmac_sha256"}
    expected = _mac(secret, body)
    if not hmac.compare_digest(expected, population.get("population_hmac_sha256", "")):
        raise BenchmarkError("PRIVATE_POPULATION_MAC_MISMATCH")
    if body.get("schema_version") != SCHEMA_VERSION:
        raise BenchmarkError("POPULATION_SCHEMA_CHANGED")
    if body.get("scope") not in {SCOPE, "SYNTHETIC_REHEARSAL_ONLY"}:
        raise BenchmarkError("POPULATION_SCOPE_INVALID")
    _iso(body.get("population_frozen_at"))
    claimed = body.get("population_sha256")
    rest = {k: v for k, v in body.items() if k != "population_sha256"}
    if claimed != sha(canonical(rest)):
        raise BenchmarkError("POPULATION_HASH_MISMATCH")
    rows = body.get("casebook")
    bindings = body.get("sources")
    if not isinstance(rows, list) or not isinstance(bindings, dict):
        raise BenchmarkError("POPULATION_CASEBOOK_MISSING")
    if set(bindings) != set(EXPECTED_FACE_COUNTS):
        raise BenchmarkError("ORIGINAL_SOURCE_SET_CHANGED")
    if body["scope"] == SCOPE:
        if body.get("original_byte_checks_executed") is not True:
            raise BenchmarkError("ORIGINAL_BYTES_NOT_CHECKED")
        if len(rows) != sum(EXPECTED_FACE_COUNTS.values()):
            raise BenchmarkError("ORIGINAL_CENSUS_SIZE_DRIFT")
        for issuer in EXPECTED_FACE_COUNTS:
            b = bindings[issuer]
            _expected_source(issuer, b["source_pdf_sha256"],
                             b["source_face_catalog_sha256"])
            if b.get("count") != EXPECTED_FACE_COUNTS[issuer]:
                raise BenchmarkError("ORIGINAL_CENSUS_BINDING_DRIFT")
    seen_ids = set()
    seen_source = set()
    per_source = Counter()
    for row in rows:
        issuer = row.get("issuer")
        if issuer not in bindings:
            raise BenchmarkError("UNKNOWN_CASE_ISSUER")
        raw = {k: v for k, v in row.items() if k != "case_id"}
        if not hmac.compare_digest(
                _mac(secret, {"case_namespace": "RETALLY-ORIGINAL-FACE-v1", **raw}),
                row.get("case_id", "")):
            raise BenchmarkError("CASE_IDENTITY_MAC_MISMATCH")
        if row["case_id"] in seen_ids:
            raise BenchmarkError("DUPLICATE_CASE_ID")
        identity = (issuer, row.get("invoice_number"))
        if identity in seen_source:
            raise BenchmarkError("DUPLICATE_INVOICE")
        seen_ids.add(row["case_id"])
        seen_source.add(identity)
        per_source[issuer] += 1
        if row.get("source_pdf_sha256") != bindings[issuer]["source_pdf_sha256"]:
            raise BenchmarkError("CASE_SOURCE_MISMATCH")
    if per_source != Counter({k: v["count"] for k, v in bindings.items()}):
        raise BenchmarkError("PER_SOURCE_CASE_CENSUS_MISMATCH")


def _signature(body: dict, signature_b64: str, public_key_b64: str) -> None:
    # Trusted public keys must come from a separately governed local trust
    # store, NEVER the truth/prediction payload itself.
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(
            public_key_b64, validate=True))
        signature = base64.b64decode(signature_b64, validate=True)
        key.verify(signature, canonical(body))
    except (ValueError, TypeError, ImportError, KeyError, AttributeError) as exc:
        raise BenchmarkError("INDEPENDENT_SIGNER_KEY_OR_SIGNATURE_INVALID") from exc
    except Exception as exc:
        raise BenchmarkError("INDEPENDENT_SIGNER_SIGNATURE_REJECTED") from exc


def _read_artifact(artifact: dict) -> str:
    if not isinstance(artifact, dict) or set(artifact) != {
            "sha256", "path", "issuer", "source_locator"}:
        raise BenchmarkError("ORIGINAL_PROOF_DOCUMENT_METADATA_REQUIRED")
    digest = _exact_sha(artifact["sha256"])
    if not isinstance(artifact.get("issuer"), str) or not artifact["issuer"].strip():
        raise BenchmarkError("EVIDENCE_ORIGIN_REQUIRED")
    locator = artifact.get("source_locator")
    if (not isinstance(locator, str) or not locator.strip()
            or len(locator) > 256 or any(ord(c) < 32 for c in locator)):
        raise BenchmarkError("SOURCE_SPECIFIC_PROOF_LOCATOR_REQUIRED")
    p = _private_path(artifact["path"])
    if not p.is_file() or p.is_symlink() or p.stat().st_size > 20_000_000:
        raise BenchmarkError("ORIGINAL_PROOF_DOCUMENT_NOT_PRESENT")
    if sha(p.read_bytes()) != digest:
        raise BenchmarkError("ORIGINAL_PROOF_DOCUMENT_HASH_MISMATCH")
    return digest


def _validate_signed_packet(packet: dict, trust: dict,
                            roles: tuple[str, ...]) -> dict:
    if not isinstance(packet, dict) or set(packet) != {"body", "signatures"}:
        raise BenchmarkError("SIGNED_PACKET_INVALID")
    body, signatures = packet["body"], packet["signatures"]
    if not isinstance(body, dict) or not isinstance(signatures, dict):
        raise BenchmarkError("SIGNED_PACKET_SHAPE_INVALID")
    if set(signatures) != set(roles) or set(trust) != {
            "operator", "truth_owner", "reviewer_a", "reviewer_b"}:
        raise BenchmarkError("TRUST_ROLE_SET_INVALID")
    if len(set(trust.values())) != 4:
        raise BenchmarkError("INDEPENDENT_SIGNING_KEYS_MUST_BE_DISTINCT")
    for role in roles:
        _signature(body, signatures[role], trust[role])
    return body


def score_private_population(population: dict, secret: bytes,
                             model_packet: dict, truth_packet: dict,
                             trust: dict, joint_unseal_at: str) -> dict:
    """Score only signed, source-backed adjudicated cases, keep unknowns NULL.

    Even a valid packet is not proof of reviewer employment, source legal
    applicability, timestamp witnessing, buyer consent or commercial rights.
    These must be independently assessed outside this tool before publication.
    """
    verify_population(population, secret)
    model = _validate_signed_packet(model_packet, trust, ("operator",))
    truth = _validate_signed_packet(
        truth_packet, trust, ("truth_owner", "reviewer_a", "reviewer_b"))
    p_hash = population["population_sha256"]
    if model.get("population_sha256") != p_hash or truth.get("population_sha256") != p_hash:
        raise BenchmarkError("SEALED_POPULATION_DRIFT")
    if (len(set((model.get("operator_id"), truth.get("truth_owner_id"),
                 truth.get("reviewer_a_id"), truth.get("reviewer_b_id")))) != 4
            or not all(isinstance(x, str) and x.strip() for x in (
                model.get("operator_id"), truth.get("truth_owner_id"),
                truth.get("reviewer_a_id"), truth.get("reviewer_b_id")))):
        raise BenchmarkError("INDEPENDENT_ROLE_COLLISION")
    if (model.get("operator_id") == truth.get("truth_owner_id")):
        raise BenchmarkError("MODEL_AND_TRUTH_NOT_INDEPENDENT")
    begin = _iso(population["population_frozen_at"])
    unseal = _iso(joint_unseal_at)
    if not (begin <= _iso(model.get("frozen_at")) < unseal
            and begin <= _iso(truth.get("frozen_at")) < unseal):
        raise BenchmarkError("FREEZE_OR_UNSEAL_ORDER_INVALID")
    expected_ids = {row["case_id"] for row in population["casebook"]}
    mrows = model.get("cases")
    trows = truth.get("cases")
    if not isinstance(mrows, list) or not isinstance(trows, list):
        raise BenchmarkError("SEALED_CASES_MISSING")
    mi = {r.get("case_id"): r for r in mrows}
    ti = {r.get("case_id"): r for r in trows}
    if (len(mi) != len(mrows) or len(ti) != len(trows)
            or set(mi) != expected_ids or set(ti) != expected_ids):
        raise BenchmarkError("SEALED_CASE_CENSUS_MISMATCH")
    tp = tn = fp = fn = positive_review = negative_review = 0
    unsigned = unsupported = 0
    false_positive_cents = missed_positive_cents = absolute_error_cents = 0
    # Reusing one independently issued clearing/decision line to support
    # different invoice case IDs would double-count financial proof.
    used_payment_lines: set[tuple[str, str]] = set()
    used_adjudication_lines: set[tuple[str, str]] = set()
    source_counts: dict[str, dict[str, int]] = {
        issuer: {"population": 0, "scored": 0, "unresolved": 0,
                 "tp": 0, "fp": 0, "tn": 0, "fn": 0, "review": 0}
        for issuer in EXPECTED_FACE_COUNTS
    }
    source_by_id = {row["case_id"]: row for row in population["casebook"]}
    for case_id in sorted(expected_ids):
        prediction, gold = mi[case_id], ti[case_id]
        original = source_by_id[case_id]
        per_source = source_counts[original["issuer"]]
        per_source["population"] += 1
        if gold.get("source_pdf_sha256") != original["source_pdf_sha256"]:
            raise BenchmarkError("TRUTH_NOT_BOUND_TO_ORIGINAL_PDF")
        if gold.get("original_invoice_total_cents") != original["invoice_total_cents"]:
            raise BenchmarkError("TRUTH_NOT_BOUND_TO_ORIGINAL_FACE_MONEY")
        p_label, t_label = prediction.get("label"), gold.get("label")
        p_cents, t_cents = prediction.get("variance_cents"), gold.get("variance_cents")
        if p_label not in PRED_TYPES or t_label not in CASE_TYPES:
            raise BenchmarkError("UNSUPPORTED_CASE_LABEL")
        if type(t_cents) is not int or t_cents < 0 or t_cents > 10**12:
            raise BenchmarkError("TRUTH_EXACT_MONEY_REQUIRED")
        if t_label == "POSITIVE" and not t_cents:
            raise BenchmarkError("POSITIVE_GOLD_MONEY_REQUIRED")
        if t_label != "POSITIVE" and t_cents:
            raise BenchmarkError("NONPOSITIVE_GOLD_MONEY_FORBIDDEN")
        if ((p_label == "REVIEW" and p_cents is not None)
                or (p_label == "NEGATIVE" and p_cents != 0)
                or (p_label == "POSITIVE" and (type(p_cents) is not int
                                                or not 0 < p_cents <= 10**12))):
            raise BenchmarkError("PREDICTION_EXACT_MONEY_INVALID")
        _exact_sha(prediction.get("model_output_sha256"))
        if t_label == "UNRESOLVED":
            if gold.get("artifacts") not in (None, {}):
                raise BenchmarkError("UNKNOWN_CASE_CANNOT_CERTIFY_PROOF")
            unsigned += 1
            per_source["unresolved"] += 1
            unsupported += int(p_label != "REVIEW")
            continue
        if (gold.get("reviewer_a_label") not in {"POSITIVE", "NEGATIVE"}
                or gold.get("reviewer_b_label") not in {"POSITIVE", "NEGATIVE"}):
            raise BenchmarkError("INDEPENDENT_DUAL_REVIEW_MISSING")
        if (gold["reviewer_a_label"] == gold["reviewer_b_label"]
                and gold["reviewer_a_label"] != t_label):
            raise BenchmarkError("TRUTH_CONFLICTS_WITH_REVIEWER_CONSENSUS")
        if (gold["reviewer_a_label"] != gold["reviewer_b_label"]
                and len(str(gold.get("adjudication_note") or "").strip()) < 15):
            raise BenchmarkError("INDEPENDENT_REVIEW_DISAGREEMENT_NOT_RESOLVED")
        proof = gold.get("artifacts")
        if not isinstance(proof, dict) or set(proof) != set(ARTIFACTS):
            raise BenchmarkError("ORIGINAL_RATE_SHIPMENT_PAYMENT_ADJUDICATION_REQUIRED")
        proof_shas = [_read_artifact(proof[k]) for k in ARTIFACTS]
        source_sha = original["source_pdf_sha256"]
        for role, used in (("payment", used_payment_lines),
                           ("adjudication", used_adjudication_lines)):
            evidence_line = (proof[role]["sha256"], proof[role]["source_locator"])
            if evidence_line in used:
                raise BenchmarkError("DUPLICATE_INDEPENDENT_FINANCIAL_PROOF_LINE")
            used.add(evidence_line)
        per_source["scored"] += 1
        if len(set([source_sha, *proof_shas])) != 5:
            raise BenchmarkError("CORRELATED_OR_REUSED_PROOF_SOURCE")
        if p_label == "REVIEW":
            if t_label == "POSITIVE":
                positive_review += 1
                per_source["review"] += 1
                missed_positive_cents += t_cents
            else:
                negative_review += 1
                per_source["review"] += 1
        elif p_label == "POSITIVE":
            absolute_error_cents += abs(p_cents - t_cents)
            if t_label == "POSITIVE":
                tp += 1
                per_source["tp"] += 1
            else:
                fp += 1
                per_source["fp"] += 1
                false_positive_cents += p_cents
        else:
            absolute_error_cents += t_cents
            if t_label == "POSITIVE":
                fn += 1
                per_source["fn"] += 1
                missed_positive_cents += t_cents
            else:
                tn += 1
                per_source["tn"] += 1
    reviewed = tp + tn + fp + fn + positive_review + negative_review
    if population["scope"] != SCOPE:
        status = "SYNTHETIC_REHEARSAL_NOT_REAL_ACCURACY"
    elif reviewed == 0:
        status = "INDEPENDENT_TRUTH_NOT_ACQUIRED"
    elif unsupported:
        status = "UNSUPPORTED_AUTOMATIC_DECISIONS_BLOCK_RELEASE"
    else:
        status = "CONDITIONAL_SIGNED_CASE_METRICS_NOT_PUBLICATION_APPROVAL"
    report = {
        "schema_version": 1, "scope": population["scope"],
        "population_count": len(expected_ids),
        "independently_signed_case_count_with_in_memory_original_proofs": reviewed,
        "unresolved_unknown_case_count": unsigned,
        "unsupported_automatic_calls_on_unresolved": unsupported,
        "true_positive": tp, "false_positive": fp,
        "true_negative": tn, "false_negative": fn,
        "positive_review_abstentions": positive_review,
        "negative_review_abstentions": negative_review,
        "auto_decision_coverage_over_entire_population": (tp+tn+fp+fn)/len(expected_ids),
        "precision": tp/(tp+fp) if tp+fp else None,
        "recall_including_review_abstentions": (
            tp/(tp+fn+positive_review) if tp+fn+positive_review else None),
        "false_positive_rate_including_negative_reviews": (
            fp/(fp+tn+negative_review) if fp+tn+negative_review else None),
        "precision_wilson_95": _wilson(tp, tp+fp),
        "false_positive_rate_wilson_95": _wilson(fp, fp+tn+negative_review),
        "false_positive_dollars_cents": false_positive_cents,
        "missed_positive_dollars_cents": missed_positive_cents,
        "automatic_exact_money_absolute_error_cents": absolute_error_cents,
        "issuer_strata": source_counts,
        "recall_wilson_95_including_review": _wilson(
            tp, tp + fn + positive_review),
        "method_status": status,
        "signed_payload_digests": {
            "operator": sha(canonical(model)),
            "independent_truth_review": sha(canonical(truth)),
        },
        "independent_signer_real_world_identity_and_timestamp_audited": False,
        "buyer_data_reuse_and_contract_authority_legally_cleared": False,
        "existing_audit_acceptance_v2_executed": False,
        "commercial_release_approved": False,
        "verified_retally_recovered_cash_cents": 0,
        "billable_fees_cents": 0,
    }
    report["report_sha256"] = sha(canonical(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Private original-freight accuracy study")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline", action="store_true",
                      help="Validate existing aggregate original-document lab output")
    mode.add_argument("--prepare", action="store_true",
                      help="Fresh original-PDF replay to a new restricted private casebook")
    mode.add_argument("--score", action="store_true",
                      help="Evaluate a privately signed and source-backed blind packet")
    parser.add_argument("--lab-report")
    parser.add_argument("--output")
    parser.add_argument("--population")
    parser.add_argument("--predictions")
    parser.add_argument("--truth")
    parser.add_argument("--trusted-public-keys")
    parser.add_argument("--unseal-at")
    args = parser.parse_args()
    if args.baseline:
        if not args.lab_report:
            parser.error("--baseline needs --lab-report")
        receipt = baseline_receipt(json.loads(Path(args.lab_report).read_text()))
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return
    secret = os.environ.get("RETALLY_PRIVATE_BENCHMARK_HMAC_KEY", "").encode()
    _key(secret)
    if args.prepare:
        if not args.output:
            parser.error("--prepare needs --output")
        population = collect_private_population(secret)
        _save_new_private(args.output, population)
        print(json.dumps({
            "status": "PRIVATE_SOURCE_CENSUS_PREPARED_NOT_ADJUDICATED",
            "case_count": len(population["casebook"]),
            "population_sha256": population["population_sha256"],
            "scored": 0, "precision": None, "commercial_release_approved": False,
        }, sort_keys=True))
        return
    if not all((args.population, args.predictions, args.truth,
                args.trusted_public_keys, args.unseal_at)):
        parser.error("--score needs --population --predictions --truth "
                     "--trusted-public-keys --unseal-at")
    report = score_private_population(
        json.loads(_private_path(args.population).read_text()), secret,
        json.loads(_private_path(args.predictions).read_text()),
        json.loads(_private_path(args.truth).read_text()),
        json.loads(_private_path(args.trusted_public_keys).read_text()),
        args.unseal_at,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
