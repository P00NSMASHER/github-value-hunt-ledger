"""Reproduce the private, synthetic RETALLY pilot. Never uses a production database."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import sqlite3
import subprocess
import sys

from ai_business_os import retally_case_desk as desk
from ai_business_os.retally_capturebrief_pilot import build_capturebrief_preview
from ai_business_os.gopher_crm import GopherCRM, CRMUnavailable
from ai_business_os.retally_inquiry_sync import external_reference, private_db, sync
from freight.commercial_terms import calculate_recovery_fee
from recoveryworks import (
    Branch,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    RuleRef,
)
from recoveryworks.financial_events import CashEvent

HERE = Path(__file__).resolve().parent
CAPTUREBRIEF = "01520d46a90cd0b07fad1850a2873cb30374bfce"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freight_case(ref):
    ledger = DurableRecoveryLedger()
    proof = lambda name: digest((ref + ":" + name).encode())
    finding = RecoveryEngine().evaluate(
        RecoveryObservation(
            branch=Branch.FREIGHT,
            client_id="fixture-distribution",
            counterparty_id="fixture-carrier",
            reference=ref,
            currency="USD",
            expected_cents=100_000,
            actual_cents=200_000,
            rule=RuleRef(
                rule_id="fixture-rule",
                source_hash=proof("contract"),
                effective_from="2026-01-01",
                effective_to=None,
                verified_controlling=True,
                source_locator="fixture://contract",
            ),
            evidence=(
                EvidenceRef(
                    evidence_id="fixture-invoice",
                    source_hash=proof("invoice"),
                    locator="fixture://invoice",
                    kind="invoice",
                    verified=True,
                ),
            ),
            reason="OVERCHARGE",
            confidence_basis="synthetic contract and invoice",
        )
    )
    fid = finding.finding_id
    ledger.add(finding)
    ledger.approve(fid, "fixture-reviewer", "verified against simulated invoice")
    ledger.authorize(fid, "synthetic-authorization-" + ref)
    ledger.mark_claimed(fid)
    fees = [ledger.get(fid).fee_cents]
    for eid, cents, prior in (("receipt", 40_000, None), ("reversal", -10_000, "receipt")):
        new_amount = ledger.get(fid).recovered_cents + cents
        net_fee = calculate_recovery_fee(actual_recovered_cents=new_amount).recovery_fee_cents
        event = CashEvent(
            eid,
            fid,
            cents,
            net_fee - fees[-1],
            "USD",
            proof(eid),
            "fixture://" + eid,
            ledger.get(fid).updated_at,
            True,
            prior,
        )
        ledger.post_cash_event(event)
        fees.append(ledger.get(fid).fee_cents)
    bundle = ledger.export_bundle()
    restored = DurableRecoveryLedger.from_bundle(bundle)
    assert restored.journal.head_hash == ledger.journal.head_hash
    assert fees == [0, 12000, 9000] and restored.get(fid).recovered_cents == 30000
    return {
        "flagged_cents": finding.potential_recovery_cents,
        "recovery_cents": restored.get(fid).recovered_cents,
        "fee_cents": fees[-1],
        "fee_sequence": fees,
        "currency": "USD",
        "ledger_head": ledger.journal.head_hash,
        "finding_id": fid,
    }, bundle


def capture_case(checkout, work):
    if (
        subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        != CAPTUREBRIEF
    ):
        raise ValueError("CaptureBrief source pin mismatch")
    # Use its own exercised source/QA workflow; preview has no external transport.
    subprocess.run(
        [
            sys.executable,
            str(checkout / "scripts/run_simulated_pilot.py"),
            "--output-dir",
            str(work / "capturebrief"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    report = json.loads((work / "capturebrief/report.json").read_text())
    if report["passed"] is not True or not report["simulated"]:
        raise ValueError("CaptureBrief source acceptance failed")
    return report


@contextmanager
def pilot_crm(root, args, state="crm"):
    directory = root / state
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ai_business_os.gopher_pilot",
            "--binary",
            str(args.gopher),
            "--admin-binary",
            str(args.admin),
            "--state",
            str(directory),
            "--port",
            str(args.port),
        ],
        cwd=HERE.parent,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        if not select.select([proc.stdout], [], [], 30)[0] or not proc.stdout.readline().startswith(
            "Private sales pilot ready"
        ):
            raise RuntimeError("CRM bootstrap did not attest readiness")
        config = json.loads((directory / "client.json").read_text())
        client = GopherCRM(**config)
        yield client, config
    finally:
        proc.terminate()
        proc.wait(timeout=12)


def backup_db(source, target):
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as dest:
        origin.backup(dest)
    os.chmod(target, 0o600)


def populate_cases(db, receipts, money, bundle, capture):
    db.executescript(desk.SCHEMA)
    for service, ref in (
        ("freight", receipts["freight_reference"]),
        ("capturebrief", receipts["capturebrief_reference"]),
    ):
        account = "account:synthetic-distribution"
        desk.open_case(db, ref, account, "Pilot owner", date.today().isoformat())

        def evidence(kind, body):
            return desk.add_artifact(db, ref, kind, dict(fixture=True, reference=ref, **body))

        details = {
            "fit": {"service": service},
            "agreement": {
                "scope": "synthetic private preview",
                "service": service,
                "pricing": "contingency" if service == "freight" else "free founder pilot",
            },
            "authorization": {"service": service, "audience": "operator only", "external_send": False},
            "manifest": {
                "origin": "synthetic invoice + contract"
                if service == "freight"
                else "CaptureBrief pinned test corpus"
            },
            "release": {"environment": "isolated synthetic fixture"},
            "work_record": {"service": service},
            "quality": (
                {"ledger_head": money["ledger_head"]}
                if service == "freight"
                else {"upstream_pin": CAPTUREBRIEF, "quality": capture["quality"]}
            ),
            "deliverable": money
            if service == "freight"
            else {"preview": capture["preview_markdown"], "sha256": capture["preview_sha256"]},
        }
        stages = (
            ("qualified", "scoped", "ready", "fulfillment", "quality-reviewed")
            if service == "freight"
            else ("qualified", "scoped")
        )
        for stage in stages:
            for kind in desk.REQUIRED[stage]:
                evidence(kind, details[kind])
            desk.advance(db, ref, stage)
        if service == "capturebrief":
            evidence("quality", details["quality"])
            evidence("deliverable", details["deliverable"])
            desk.update_task(
                db, ref, "Pilot owner", date.today().isoformat(), "Source conflict. Operator review required."
            )
        if service == "freight":
            evidence("recovery_ledger", {"bundle": bundle})
            evidence("fee_receipts", {"collected_cents": 0, "currency": "USD", "receipts": []})
        try:
            desk.advance(db, ref, "delivered")
        except ValueError:
            pass
        else:
            raise AssertionError("preview was marked delivered without a delivery receipt")
        artifact = db.execute(
            "SELECT digest FROM case_artifacts WHERE reference=? AND kind='deliverable'", (ref,)
        ).fetchone()[0]
        try:
            desk.case_artifact(db, "account:unrelated", ref, "deliverable", artifact)
        except ValueError:
            pass
        else:
            raise AssertionError("account isolation failed")
    register = desk.customer_register(db)
    assert len(register["accounts"]) == 1 and len(register["engagements"]) == 2


def run(args):
    root = args.workspace.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    source, state = root / "intake.sqlite", root / "desk.sqlite"
    receipts = json.loads(
        subprocess.check_output(["node", str(HERE / "retally_inquiry_fixture.mjs"), str(source)], text=True)
    )
    with private_db(source, readonly=True) as db:
        source_id = db.execute("SELECT source_id FROM retally_fixture_identity").fetchone()[0]

    def replay(client, config, source_path=source, state_path=state):
        return sync(
            source_path,
            state_path,
            client,
            namespace="synthetic",
            destination=client.base_url,
            owner=config["owner_id"],
        )

    with pilot_crm(root, args) as (client, config):
        pass
    try:
        replay(client, config)
    except CRMUnavailable:
        pass
    else:
        raise AssertionError("expected an actual offline CRM")
    with private_db(state, readonly=True) as db:
        assert db.execute("SELECT count(*) FROM delivery WHERE phase='lead'").fetchone()[0] == 2
    with pilot_crm(root, args) as (client, config):
        assert replay(client, config) == {"done": 2}
        assert replay(client, config) == {"done": 2}
        ids = {}
        for ref in (receipts["freight_reference"], receipts["capturebrief_reference"]):
            key = external_reference(source_id, ref)
            lead = client.find_lead(key)
            task = client.find_task(key, lead)
            assert lead and task
            ids[ref] = (lead, task)
    money, bundle = freight_case(receipts["freight_reference"])
    golden = capture_case(args.capturebrief, root)
    capture = build_capturebrief_preview(
        args.capturebrief,
        source,
        receipts["capturebrief_reference"],
        root / "capture-review",
        source_pdf=args.source_pdf,
    )
    from ai_business_os.retally_postmill import open_calendar, import_readback

    calendar = open_calendar(state)
    try:
        import_readback(calendar, args.postmill_receipt)
    finally:
        calendar.close()
    with private_db(state) as db:
        populate_cases(db, receipts, money, bundle, capture)
    restore = root / "restore"
    restore.mkdir(mode=0o700)
    backup_db(source, restore / "intake.sqlite")
    backup_db(state, restore / "desk.sqlite")
    (restore / "crm").mkdir(mode=0o700)
    backup_db(root / "crm/gopher.sqlite", restore / "crm/gopher.sqlite")
    for name in ("server.json", "login.json", "client.json"):
        shutil.copy2(root / "crm" / name, restore / "crm" / name)
    with pilot_crm(restore, args) as (client, config):
        from ai_business_os.gopher_pilot import rotate_restored_key

        config = rotate_restored_key(restore / "crm", config)
        client = GopherCRM(**config)
        assert replay(client, config, restore / "intake.sqlite", restore / "desk.sqlite") == {"done": 2}
        for ref, (lead, task) in ids.items():
            key = external_reference(source_id, ref)
            assert (client.find_lead(key), client.find_task(key, lead)) == (lead, task)
    with private_db(restore / "desk.sqlite", readonly=True) as db:
        assert len(desk.customer_register(db)["engagements"]) == 2
        stored = db.execute("SELECT content FROM case_artifacts WHERE kind='recovery_ledger'").fetchone()[0]
        assert (
            DurableRecoveryLedger.from_bundle(json.loads(stored)["bundle"]).journal.head_hash
            == money["ledger_head"]
        )
    result = {
        "environment": "local synthetic",
        "intake": receipts,
        "crm_readback": ids,
        "crm_offline_recovered": True,
        "restore_readback": True,
        "restored_key_rotated": True,
        "freight": money,
        "fee_cash_collected_cents": 0,
        "capturebrief": {
            "source_pin": CAPTUREBRIEF,
            "source_matrix_passed": golden["passed"],
            "golden_preview_files": golden["golden_delivery_check"]["file_count"],
            "case_id": capture["case_id"],
            "quality": capture["quality"],
            "preview_sha256": capture["preview_sha256"],
            "pricing": capture["pricing"],
            "external_send_authorized": False,
        },
        "real_customers": 0,
        "real_recovered_cents": 0,
        "external_sends": 0,
    }
    save(root / "acceptance.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "gopher", "admin", "capturebrief"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument(
        "--postmill-receipt",
        type=Path,
        help="verified fresh synthetic draft readback from Postmill acceptance",
    )
    parser.add_argument("--source-pdf", type=Path, help="optional cached, hash-checked official public PDF")
    parser.add_argument("--port", type=int, default=19823)
    run(parser.parse_args())
