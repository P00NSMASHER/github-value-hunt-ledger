"""Build a private, source-limited CaptureBrief preview for a committed synthetic group inquiry."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

PIN = "01520d46a90cd0b07fad1850a2873cb30374bfce"
NOTICE = "https://sam.gov/opp/0d961fc227d34d4da9a895f941e48a1e/view"
ASSUMPTION = "The response deadline has not changed."


def build_capturebrief_preview(checkout, intake_db, reference, output_dir, source_pdf=None):
    """Return the bound result and write a private preview. A cached public PDF enables offline replay."""
    checkout = Path(checkout).resolve()
    if subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() != PIN:
        raise ValueError("CaptureBrief source revision mismatch")
    subprocess.run(["git", "-C", str(checkout), "diff", "--quiet", "HEAD", "--", "scripts", "capturebrief_core"], check=True)
    if not re.fullmatch(r"RA-[0-9]{8}-[A-F0-9]{8}", reference):
        raise ValueError("invalid inquiry reference")
    source = Path(intake_db).resolve(strict=True)
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute("""SELECT i.company_name,i.work_email,i.accepted_at,i.details_json,i.fingerprint
                            FROM inquiries i JOIN retally_inquiry_feed f ON f.reference=i.reference
                            WHERE i.reference=?""", (reference,)).fetchone()
    if not row:
        raise ValueError("no committed source inquiry")
    company, email, accepted, details, fingerprint = row
    details = json.loads(details)
    if (not email.endswith("@example.invalid") or details.get("inquiryKind") != "group_contact"
            or details.get("business") != "capturebrief" or details.get("consent") is not True
            or "synthetic" not in details.get("message", "").lower()):
        raise ValueError("only consented synthetic CaptureBrief requests are eligible")

    # Use the pinned service's parser, QA, fulfillment planner and report guard.
    sys.path.insert(0, str(checkout))
    try:
        from capturebrief_core import request_draft as draft
        from capturebrief_core.free_trial import inspect_free_check, build_free_check_report
        from capturebrief_core.fulfillment_plan import build_fulfillment_plan
        from capturebrief_core.delivery_readiness import evaluate_delivery_readiness
        from capturebrief_core.render import render_markdown
        from scripts.prepare_founder_review_packet import SOURCE_BYTES, SOURCE_SHA, SOL, source_findings
        from scripts.verify_federal_pilot_public_case import fetch_official_pdf
        from pypdf import PdfReader
    finally:
        sys.path.pop(0)
    if Path(draft.__file__).resolve().parent.parent != checkout:
        raise ValueError("unexpected CaptureBrief import root")
    when = datetime.fromtimestamp(accepted, timezone.utc)
    # The original group form asks for contact. The operator adds a labeled test
    # scope separately; no customer declaration or real free-check slot is created.
    scope_draft = "\n".join([draft.HEADER, "", "Purchase status (customer-reported, not verified): " + draft.FREE_CLAIM,
                             "Company: " + company, "Work email: " + email, "Public opportunity link: " + NOTICE,
                             "Current posture: HOLD", "", draft.ASSUMPTIONS, "1. " + ASSUMPTION, "",
                             draft.CONFIRMATION, "", draft.FREE_END])
    case, claim = draft.create_unverified_case(scope_draft, submitted_at=when.isoformat())
    if len(case["assumptions"]) != 1 or claim["trial_admission_authorized"]:
        raise ValueError("unexpected free-pilot scope or admission")
    if source_pdf is None:
        pdf, _ = fetch_official_pdf()
    else:
        with Path(source_pdf).open("rb") as stream:
            pdf = stream.read(SOURCE_BYTES + 1)
    if len(pdf) != SOURCE_BYTES or hashlib.sha256(pdf).hexdigest() != SOURCE_SHA:
        raise ValueError("public original failed pinned byte integrity")
    pages = PdfReader(io.BytesIO(pdf), strict=True).pages
    findings = source_findings([p.extract_text() or "" for p in pages])
    conflict = next(f for f in findings if f["code"] == "DEADLINE_CONFLICT")
    # Report the original's conflict but leave the controlling deadline UNPROVEN.
    case["assumptions"][0].update(finding=conflict["finding"],
                                 next_action="Review the complete SAM action family and subsequent amendments.")
    readiness = evaluate_delivery_readiness(case, now=when)
    plan = build_fulfillment_plan(case, now=when)
    check = inspect_free_check(case, now=when)
    if readiness.eligible or not readiness.blocker_codes or check["state"] != "BLOCKED_NO_RESERVATION":
        raise ValueError("source-limited synthetic inquiry unexpectedly eligible for release")

    root = Path(output_dir).expanduser().absolute()
    if any(p.is_symlink() or (p / ".git").exists() for p in (root, *root.parents)):
        raise ValueError("private preview storage required outside Git")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077 or root.stat().st_uid != os.getuid():
        raise ValueError("use owner-only preview storage")
    artifact = root / f"{reference}.preview.md"
    if artifact.is_symlink():
        raise ValueError("unsafe preview destination")
    protected = root / f"{reference}.customer.md"
    try:
        build_free_check_report(case, protected, database_path=root / "trial.sqlite", now=when)
    except ValueError as error:
        if "blocked by reservation or source evidence" not in str(error):
            raise
    else:
        raise ValueError("customer report gate failed")
    if protected.exists() or protected.with_name(protected.name + ".receipt.json").exists():
        raise ValueError("customer output exists for held inquiry")
    preview = (f"# CaptureBrief supervised review preview\n\nSynthetic private operator review for {reference}.\n\n"
               f"## Original deadline conflict\n\nTreasury RFQ {SOL}, page 1 gives November 9, 2026 at 10:00 a.m. ET. "
               "Page 3 gives November 5, 2026 at noon. The controlling deadline remains unresolved. "
               "A reviewer must inspect the full action and amendment history.\n\n"
               f"Official notice {NOTICE}\n\nOriginal SHA-256 {SOURCE_SHA}\n\n" + render_markdown(case, readiness.audit, now=when))
    content = preview.encode()
    try:
        with artifact.open("xb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
    except FileExistsError:
        if artifact.read_bytes() != content:
            raise ValueError("preview source or scope changed")
    if artifact.read_bytes() != content:
        raise ValueError("preview readback mismatch")
    return {"passed": True, "upstream_pin": PIN, "reference": reference, "case_id": case["case_id"],
            "source_fingerprint": fingerprint, "scope_origin": "synthetic operator supplement to accepted inquiry",
            "validated_scope": {"offer": claim["requested_offer"], "public_opportunity": NOTICE,
                                "assumption": ASSUMPTION, "assumption_count": 1},
            "pricing": {"currency": "USD", "amount_due_cents": check["amount_due_cents"], "watch_included": check["watch_included"],
                        "automatic_upgrade_authorized": check["automatic_upgrade_authorized"],
                        "separate_founding_offer_cents": 14900, "collected_cents": 0},
            "quality": {"original_sha256": SOURCE_SHA, "original_pages": len(pages), "original_bytes": len(pdf),
                        "source_conflict": conflict, "fulfillment_state": plan["fulfillment_state"],
                        "release_state": readiness.audit.release_state, "blockers": list(readiness.blocker_codes),
                        "reservation_state": check["state"], "customer_report_creation_blocked": True},
            "preview_sha256": hashlib.sha256(content).hexdigest(), "preview_markdown": preview,
            "customer_release_authorized": False, "external_send_authorized": False, "real_enrollments": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("checkout", "intake_db", "reference", "output_dir"):
        parser.add_argument(key)
    parser.add_argument("--source-pdf")
    result = build_capturebrief_preview(**vars(parser.parse_args()))
    del result["preview_markdown"]
    print(json.dumps(result, indent=2))
