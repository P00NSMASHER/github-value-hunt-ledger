"""Fail-closed operator preflight for RETALLY's first real pilot.

The preflight consolidates the canonical acceptance ledger into an ordered
operator packet. It is read-only: it cannot sign, approve, contact, ingest,
deploy, bill, or turn repository strings into independent authorization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.commercial.first_customer_gate import DEFAULT, evaluate


PILOT_CRITICAL_PATH = ("R22", "R23", "R24", "R25", "R26", "R27", "R37")
EVENT_STAGE_EVIDENCE = ("R32", "R33", "R34")
OPTIONAL_AUTOMATION = ("R28", "R29", "R30", "R31", "R35")

STAGES = (
    {
        "id": "public_manual_discovery",
        "label": "Public information and manual non-sensitive discovery",
        "required": (),
        "external_release": False,
    },
    {
        "id": "proposal_and_contract",
        "label": "Named proposal and binding agreement",
        "required": ("R22", "R23", "R24", "R37"),
        "external_release": True,
    },
    {
        "id": "confidential_intake",
        "label": "Confidential buyer records intake",
        "required": PILOT_CRITICAL_PATH,
        "external_release": True,
    },
    {
        "id": "manual_audit_and_report",
        "label": "Manual audit and customer report",
        "required": PILOT_CRITICAL_PATH,
        "external_release": True,
    },
    {
        "id": "customer_authorized_claim",
        "label": "Customer-authorized recovery action",
        "required": PILOT_CRITICAL_PATH,
        "external_release": True,
        "additional_hold": "claim_specific_customer_approval_required",
    },
    {
        "id": "posted_recovery",
        "label": "Posted cash or applied credit recognition",
        "required": PILOT_CRITICAL_PATH + ("R32",),
        "external_release": True,
    },
    {
        "id": "fee_invoice",
        "label": "Fee invoice issuance",
        "required": PILOT_CRITICAL_PATH + ("R32", "R33"),
        "external_release": True,
    },
    {
        "id": "closure",
        "label": "Case closure, access revocation and retention",
        "required": PILOT_CRITICAL_PATH + EVENT_STAGE_EVIDENCE,
        "external_release": True,
    },
)


def _requirement_index(snapshot: dict) -> dict[str, dict]:
    rows = snapshot["mission_acceptance"]["requirements"]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("acceptance ledger must contain requirement objects")
    indexed = {row.get("id"): row for row in rows}
    if None in indexed or len(indexed) != len(rows):
        raise ValueError("acceptance ledger contains missing or duplicate IDs")
    return indexed


def _validate_scorecard(snapshot: dict, rows: dict[str, dict]) -> None:
    score = snapshot["mission_acceptance"]["scorecard"]
    actual = {
        state: sum(row.get("status") == state for row in rows.values())
        for state in ("PASS", "BLOCKED", "FAIL")
    }
    for state, count in actual.items():
        if score.get(state) != count:
            raise ValueError(f"scorecard {state} count does not match requirement rows")
    if score.get("total") != len(rows) or sum(actual.values()) != len(rows):
        raise ValueError("scorecard total does not match requirement rows")


def build_preflight(snapshot: dict) -> dict:
    """Build a stage-ordered packet without granting real-world authority."""
    gate = evaluate(snapshot)
    rows = _requirement_index(snapshot)
    _validate_scorecard(snapshot, rows)
    referenced = set(PILOT_CRITICAL_PATH + EVENT_STAGE_EVIDENCE + OPTIONAL_AUTOMATION + ("R36",))
    missing = referenced - rows.keys()
    if missing:
        raise ValueError("pilot preflight is missing requirement IDs: " + ", ".join(sorted(missing)))

    stage_results = []
    for stage in STAGES:
        blockers = [key for key in stage["required"] if rows[key].get("status") != "PASS"]
        if stage["id"] == "public_manual_discovery":
            prerequisites_met = gate["zero_spend_public_manual_profile"]["ready"]
            action_available = prerequisites_met
        else:
            prerequisites_met = not blockers and not stage.get("additional_hold")
            # This repository is evidence preparation, not a signature or
            # authenticated release authority. An operator must validate the
            # actual evidence and authorize the exact action out of band.
            action_available = False
        stage_results.append({
            "id": stage["id"],
            "label": stage["label"],
            "ledger_prerequisites_met": prerequisites_met,
            "action_available_now": action_available,
            "blocking_requirement_ids": blockers,
            "additional_hold": stage.get("additional_hold"),
            "external_release_required": stage["external_release"],
        })

    def cards(ids: tuple[str, ...]) -> list[dict]:
        return [{
            "id": key,
            "status": rows[key]["status"],
            "requirement": rows[key]["requirement"],
            "next_action": rows[key].get("required_owner_action"),
            "evidence": rows[key].get("evidence"),
        } for key in ids]

    return {
        "classification": "READ_ONLY_FIRST_PILOT_PREFLIGHT",
        "source_as_of": snapshot["as_of"],
        "scorecard": snapshot["mission_acceptance"]["scorecard"],
        "available_now": {
            "public_information_site": True,
            "manual_user_sent_non_sensitive_email": True,
            "automated_intake": False,
            "confidential_customer_intake": False,
            "customer_service_kickoff": False,
            "financial_operations": False,
        },
        "new_external_spend_authorized_usd": "0.00",
        "stages": stage_results,
        "pilot_critical_path": cards(PILOT_CRITICAL_PATH),
        "event_stage_evidence": cards(EVENT_STAGE_EVIDENCE),
        "optional_automation_held": cards(OPTIONAL_AUTOMATION),
        "resolved_artifact_control": cards(("R36",))[0],
        "completion_record_fields": (
            "stable non-secret evidence reference",
            "authorized verifier identity",
            "timezone-aware verification timestamp",
            "exact customer, scope and authority",
        ),
        "source_only_customer_authorization": False,
        "not_a_signature_or_release_system": True,
    }


def render_markdown(packet: dict) -> str:
    lines = [
        "# RETALLY first-pilot activation packet",
        "",
        f"Canonical evidence date: **{packet['source_as_of']}**  ",
        "Classification: **read-only, fail-closed operator preflight**",
        "",
        "## Available now",
        "",
        "The existing public information site and a user-sent, non-sensitive email conversation are available at **$0 new external spend**. Automated intake, confidential records, customer work, carrier action, financial posting and billing remain unavailable.",
        "",
        "## Activation sequence",
        "",
        "| Stage | State now | Blocking evidence |",
        "| --- | --- | --- |",
    ]
    for stage in packet["stages"]:
        state = "AVAILABLE" if stage["action_available_now"] else "HOLD"
        blockers = ", ".join(stage["blocking_requirement_ids"]) or stage.get("additional_hold") or "None"
        lines.append(f"| {stage['label']} | **{state}** | {blockers} |")
    lines.extend(["", "## First-pilot critical path", ""])
    for card in packet["pilot_critical_path"]:
        lines.append(f"- [ ] **{card['id']} — {card['requirement']}**: {card['next_action']}")
    lines.extend(["", "## Evidence produced only after real events", ""])
    for card in packet["event_stage_evidence"]:
        lines.append(f"- [ ] **{card['id']} — {card['requirement']}**: {card['next_action']}")
    lines.extend(["", "## Optional automation held outside the manual pilot", ""])
    for card in packet["optional_automation_held"]:
        lines.append(f"- **{card['id']} — {card['requirement']}**: {card['status']}")
    lines.extend([
        "",
        "## Completion record required for every released gate",
        "",
    ])
    for field in packet["completion_record_fields"]:
        lines.append(f"- {field}")
    lines.extend([
        "",
        "Repository text, checkboxes, simulated reviewers and hashes do not constitute a signature, independent review or release decision. The exact real-world action must be approved through the applicable trusted channel.",
        "",
    ])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--require-stage", choices=tuple(stage["id"] for stage in STAGES))
    args = parser.parse_args(argv)
    packet = build_preflight(json.loads(args.source.read_text(encoding="utf-8")))
    print(render_markdown(packet) if args.format == "markdown" else json.dumps(packet, indent=2, sort_keys=True))
    if args.require_stage:
        stage = next(item for item in packet["stages"] if item["id"] == args.require_stage)
        if not stage["action_available_now"]:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
