from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


def parse_matched_benchmark_tasks(scoreboard: str) -> int:
    match = re.search(
        r"Matched tasks scored:\s*\*\*(\d+)\*\*",
        scoreboard,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else 0


def parse_matched_task_arms(scoreboard: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    pattern = re.compile(
        r"^\|\s*(\d{2})\s*\|\s*(CONTROL|EXPERIMENT)\s*\|",
        re.IGNORECASE | re.MULTILINE,
    )
    for match in pattern.finditer(scoreboard):
        task_id = match.group(1)
        arm = match.group(2).upper()
        out.setdefault(task_id, set()).add(arm)
    return out


def unmatched_benchmark_tasks(
    scoreboard: str,
    *,
    expected_tasks: int = 50,
) -> list[dict[str, Any]]:
    arms = parse_matched_task_arms(scoreboard)
    rows: list[dict[str, Any]] = []
    for index in range(1, expected_tasks + 1):
        task_id = f"{index:02d}"
        seen = arms.get(task_id, set())
        if {"CONTROL", "EXPERIMENT"}.issubset(seen):
            continue
        rows.append(
            {
                "task_id": task_id,
                "completed_arms": sorted(seen),
                "missing_arms": sorted(
                    {"CONTROL", "EXPERIMENT"} - seen
                ),
            }
        )
    return rows


def count_shadow_runs(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if not line.startswith("##"):
            continue
        if re.search(r"\brun\s+\d+\b", line, re.IGNORECASE):
            count += 1
    return count


def build_restart_readiness(
    *,
    split_status: Mapping[str, Any],
    activation_metrics: Mapping[str, Any],
    packets: Mapping[str, Any],
    scoreboard_text: str,
    shadow_results: Mapping[str, str],
    execution_claim_history: Sequence[Mapping[str, Any]] = (),
    required_matched_tasks: int = 50,
    required_shadow_runs: int = 15,
) -> dict[str, Any]:
    matched = parse_matched_benchmark_tasks(scoreboard_text)
    unmatched_tasks = unmatched_benchmark_tasks(
        scoreboard_text,
        expected_tasks=required_matched_tasks,
    )
    shadow_by_lane = {
        lane: count_shadow_runs(text)
        for lane, text in shadow_results.items()
    }
    shadow_total = sum(shadow_by_lane.values())

    packet_rows = packets.get("packets") or []
    unpaired = packets.get("unpaired_recommendations") or []
    packets_ready = (
        packets.get("mode") == "precommit_only"
        and packets.get("policy_effect") == "none"
        and packets.get("activates_work") is False
        and packets.get("partition_selection_allowed") is False
        and len(packet_rows) > 0
        and len(unpaired) == 0
        and all(
            row.get("status") == "PRECOMMITTED_ADVISORY"
            and row.get("execution_authority") is False
            and row.get("requires_generated_claim") is True
            and row.get("manual_work_can_complete_packet") is False
            and row.get("partition_unknown_until_ingestion") is True
            for row in packet_rows
        )
    )

    split_ready = (
        split_status.get("partition_method") == "hmac-sha256-v1"
        and split_status.get("key_commitment_active") is True
        and split_status.get("secret_available") is True
        and not (split_status.get("issues") or [])
        and not (split_status.get("pending_claim_ids") or [])
    )
    benchmark_ready = (
        matched >= required_matched_tasks
        and not unmatched_tasks
    )
    shadow_ready = shadow_total >= required_shadow_runs
    no_current_activations = (
        int(activation_metrics.get("current_activations") or 0) == 0
    )
    active_generated_claim_ids = sorted(
        str(row.get("claim_id"))
        for row in execution_claim_history
        if row.get("routing_mode") == "generated"
        and row.get("status") in {"CLAIMED", "RUNNING"}
        and isinstance(row.get("claim_id"), str)
        and row.get("claim_id")
    )
    no_active_generated_claims = not active_generated_claim_ids

    blockers: list[dict[str, Any]] = []
    if not packets_ready:
        blockers.append(
            {
                "code": "measurement_packets_not_ready",
                "action": (
                    "Regenerate and validate learning measurement packets; "
                    "all curriculum recommendations must pair to an "
                    "authorized search seed."
                ),
            }
        )
    if split_status.get("key_commitment_active") is not True:
        blockers.append(
            {
                "code": "split_key_commitment_inactive",
                "action": (
                    "Configure the GitHub Actions repository secret "
                    "TI_TRAINING_SPLIT_KEY, then rerun Technology "
                    "Intelligence so the public commitment is generated."
                ),
            }
        )
    if split_status.get("secret_available") is not True:
        blockers.append(
            {
                "code": "split_secret_unavailable",
                "action": (
                    "Make TI_TRAINING_SPLIT_KEY available to the Technology "
                    "Intelligence workflow; never put its value in repository "
                    "files, prompts, logs, or worker-visible state."
                ),
            }
        )
    issues = split_status.get("issues") or []
    pending = split_status.get("pending_claim_ids") or []
    if issues or pending:
        blockers.append(
            {
                "code": "split_receipt_debt",
                "issue_count": len(issues),
                "pending_claim_count": len(pending),
                "action": (
                    "After the split key is configured, regenerate receipts "
                    "and require the split-status validator to clear all "
                    "pending generated claims before canary activation."
                ),
            }
        )
    if not benchmark_ready:
        blockers.append(
            {
                "code": "frozen_benchmark_incomplete",
                "matched_tasks": matched,
                "required_matched_tasks": required_matched_tasks,
                "unmatched_task_ids": [
                    row["task_id"]
                    for row in unmatched_tasks
                ],
                "unmatched_tasks": unmatched_tasks,
                "action": (
                    "Finish the remaining frozen benchmark experiment "
                    "conditions in clean contexts before using adaptive "
                    "measurement packets."
                ),
            }
        )
    if not shadow_ready:
        blockers.append(
            {
                "code": "shadow_run_gate_incomplete",
                "shadow_runs": shadow_total,
                "required_shadow_runs": required_shadow_runs,
                "action": "Accumulate the required combined shadow runs.",
            }
        )
    if not no_current_activations:
        blockers.append(
            {
                "code": "existing_generated_activations_present",
                "current_activations": int(
                    activation_metrics.get("current_activations") or 0
                ),
                "action": (
                    "Resolve or release existing generated activations before "
                    "starting a measurement canary."
                ),
            }
        )
    if not no_active_generated_claims:
        blockers.append(
            {
                "code": "active_generated_claims_present",
                "active_generated_claim_count": len(
                    active_generated_claim_ids
                ),
                "active_generated_claim_ids": active_generated_claim_ids,
                "action": (
                    "Complete, fail, expire, or release active generated "
                    "claims before starting a measurement canary."
                ),
            }
        )

    if blockers:
        state = "BLOCKED"
    else:
        state = "AWAITING_EXPLICIT_USER_APPROVAL"

    return {
        "schema_version": 1,
        "mode": "restart_readiness_only",
        "activates_work": False,
        "changes_automation_state": False,
        "explicit_user_approval_required": True,
        "state": state,
        "canary": {
            "packet_count": len(packet_rows),
            "maximum_initial_packet_runs": min(3, len(packet_rows)),
            "one_generated_claim_per_packet": True,
            "retry_for_partition_forbidden": True,
            "manual_completion_forbidden": True,
            "post_ingestion_split_receipt_required": True,
        },
        "gates": {
            "measurement_packets_ready": packets_ready,
            "split_receipt_system_ready": split_ready,
            "benchmark_complete": benchmark_ready,
            "shadow_run_gate_complete": shadow_ready,
            "no_current_activations": no_current_activations,
            "no_active_generated_claims": no_active_generated_claims,
        },
        "evidence": {
            "matched_benchmark_tasks": matched,
            "required_matched_benchmark_tasks": required_matched_tasks,
            "unmatched_benchmark_task_ids": [
                row["task_id"]
                for row in unmatched_tasks
            ],
            "unmatched_benchmark_tasks": unmatched_tasks,
            "shadow_runs_by_lane": shadow_by_lane,
            "shadow_runs_total": shadow_total,
            "required_shadow_runs": required_shadow_runs,
            "split_key_commitment_active": bool(
                split_status.get("key_commitment_active")
            ),
            "split_secret_available": bool(
                split_status.get("secret_available")
            ),
            "split_receipts": int(split_status.get("receipts") or 0),
            "pending_split_claims": len(pending),
            "current_activations": int(
                activation_metrics.get("current_activations") or 0
            ),
            "active_generated_claim_count": len(
                active_generated_claim_ids
            ),
            "active_generated_claim_ids": active_generated_claim_ids,
        },
        "blockers": blockers,
        "activation_contract": (
            "This artifact never activates a hunter. If all machine gates "
            "become true, remain AWAITING_EXPLICIT_USER_APPROVAL. Only a "
            "separate explicit user instruction may change scheduled-task "
            "state or begin the canary."
        ),
    }


def validate_restart_readiness(
    report: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if report.get("mode") != "restart_readiness_only":
        errors.append("mode_must_be_restart_readiness_only")
    if report.get("activates_work") is not False:
        errors.append("readiness_must_not_activate_work")
    if report.get("changes_automation_state") is not False:
        errors.append("readiness_must_not_change_automation_state")
    if report.get("explicit_user_approval_required") is not True:
        errors.append("explicit_user_approval_must_be_required")

    gates = report.get("gates") or {}
    blockers = report.get("blockers") or []
    machine_ready = all(
        gates.get(key) is True
        for key in (
            "measurement_packets_ready",
            "split_receipt_system_ready",
            "benchmark_complete",
            "shadow_run_gate_complete",
            "no_current_activations",
            "no_active_generated_claims",
        )
    )
    expected_state = (
        "AWAITING_EXPLICIT_USER_APPROVAL"
        if machine_ready
        else "BLOCKED"
    )
    unmatched = (
        report.get("evidence") or {}
    ).get("unmatched_benchmark_task_ids") or []
    if gates.get("benchmark_complete") is True and unmatched:
        errors.append("benchmark_complete_with_unmatched_tasks")
    if report.get("state") != expected_state:
        errors.append("restart_state_mismatch")
    if machine_ready and blockers:
        errors.append("machine_ready_report_has_blockers")
    if not machine_ready and not blockers:
        errors.append("blocked_report_requires_blockers")

    canary = report.get("canary") or {}
    if canary.get("one_generated_claim_per_packet") is not True:
        errors.append("one_claim_per_packet_required")
    if canary.get("retry_for_partition_forbidden") is not True:
        errors.append("partition_retry_must_be_forbidden")
    if canary.get("manual_completion_forbidden") is not True:
        errors.append("manual_completion_must_be_forbidden")
    if canary.get("post_ingestion_split_receipt_required") is not True:
        errors.append("split_receipt_must_be_required")

    return errors
