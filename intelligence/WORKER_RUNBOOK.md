# Worker runbook

This is the operating bridge for the existing ChatGPT/GitHub hunters. It does not deploy or activate the staged production runtime. Current templates, schemas, event logs and validated generated packets outrank version numbers copied into prose.

## 1. Resolve phase before reading research memory

The automation's frozen benchmark instructions always run first. Until its assigned benchmark tasks finish, use only its allowed protocol/task/results/state/skill inputs; do not read the scoreboard, other arm, gold, this production plan or private candidate catalogs for answers. Do not change the frozen task, budget or scoring protocol. A context exposed to other-arm answers is unsuitable for remaining benchmark tasks; record the blocker and use the next clean scheduled context.

Hunts 10, 12 and 14 retain their post-benchmark shadow missions and write restrictions. Other completed benchmark hunters use the live path below. Hunt 15 scores/integrates; it never performs a blinded experiment after reading gold. No fleet-wide production cutover is implied. The launch gates remain in production/STATUS.md.

## 2. Select one useful assignment

Read intelligence/HUNTER_MISSION.md and the relevant current HUNT_PLAN packet. Preserve the original lane as a fallback specialty, not a reason to duplicate another worker. Read current capability/experiment/STOP status before execution. Generated scores are scheduling priorities.

Use work_action and its acceptance_target:
- search: discover a missing implementation with its domain anchors;
- verify_artifact: fetch/read the specified authoritative artifact and verify the concrete missing evidence;
- execute_fixture: perform the permitted synthetic/read-only experiment, recording command, revision and result;
- await_external: record the external prerequisite and stop; do not substitute another broad search;
- verification/challenge actions: follow the explicitly scoped candidate or hypothesis packet; no independent-verification claim without an independently checked frozen candidate.

For unknown/stale task contracts, derive a narrow question from current source evidence and document a manual plan. Do not infer buyer authorization, certification or external access from a rank.

## 3. Coordinate work honestly

For a generated route:
1. Append fresh READY to intelligence/worker_presence_events/HUNTER-XX.jsonl using the latest file SHA (helper: tools/ti_worker_presence_event.py).
2. Let the normal validated intelligence build materialize fresh activation/dispatch. Read intelligence/activation_claim_packets.jsonl and recheck expiry against current UTC. If a packet is absent/stale, do not invent one.
3. Acquire the exact assignment using tools/ti_worker_claim.py or its connector-equivalent append-only CLAIM with the packet's actual fields. Fetch the latest slot event log before writing, preserve existing events, retry a SHA conflict only after rereading. A successful write alone is not a valid lease: confirm the event is accepted by the execution reducer before beginning.
4. START, heartbeat as needed, and copy real claim/assignment/routing/activation provenance into telemetry.

A benchmark/shadow worker is BUSY in that phase, not READY for live allocation. A scheduled task running is not evidence that all 14 logical workers are available.

If runtime/connector limitations prevent fresh generated activation, the existing explicit manual_override path is available for a real currently claimable assignment, with a specific reason. It still needs a valid current lease and provenance; it is excluded from generated-route learning. If no safe claim can be persisted, do bounded unclaimed research in assigned catalogs and log unallocated telemetry. Never label it generated or complete another worker's claim. Do not churn READY events or block the whole run waiting for CI.

## 4. Save evidence and one immutable run

Write detailed source evidence to the assigned lane catalog or a uniquely named referral. Preserve sibling content with optimistic file-SHA updates. For every materially completed live run, create exactly one new UTF-8 JSON object at intelligence/search_run_spool/<safe-unique-run-id>.json.

Start with tools/ti_prepare_run.py for an honest draft (see --help), then use SEARCH_RUN_TEMPLATE.json plus schemas/search_run.schema.json for current field meanings; remove placeholder candidate rows and invented provenance. Record the actual work_action, measured denominators, actual queries/surfaces, dispositions, stop reason, elapsed/tool effort if observed and durable_evidence_path. Non-search fixture/artifact work is excluded from discovery-yield comparisons and remains eligible for portfolio/outcome evidence. Set fields according to what actually happened: generated claims carry exact packet provenance; manual/unallocated work uses explicit non-generated modes. Do not downgrade or inflate historical schema metadata to pass validation.

Spool files are immutable submissions. The single CI/integrator writer uses tools/ti_ingest_runs.py --write to idempotently append valid new IDs to search_runs.jsonl. Exact replay adds no row. A conflicting ID or malformed new submission blocks intake; preserve both records and reconcile explicitly. Workers do not race replacing the shared canonical file.

For claimed work, only append COMPLETE after the canonical run is present and its claim/assignment provenance validates. Pending intake is pending completion, not success. An expired claim cannot be completed retroactively; preserve the evidence and report the lifecycle issue. Use FAIL/RELEASE for genuine blocking states. Record unmeasured work without synthetic success events.

## 5. Close the loop

A discovery is not a completed experiment. Submit experiment result evidence and true origin_search_ids for integrator review into outcomes.jsonl/OUTCOMES.md. No predicted revenue enters realized-value fields. Generated reports rebuild from canonical events.

End with a concise change report: best evidence or useful no-find; capability/experiment changed; what was actually tested; durable record path; blocker; one next question. Do not report a submission, promotion, claim, merge, independent verification or deployment unless readback proves it happened.

## Integrator procedure

Keep the frozen benchmark scoring duty first. Then:
1. Review new immutable submissions/referrals and intake errors. Never turn prospective unknowns into invented denominators; preserve explicit retrospective repairs.
2. Run intake before the existing sync/report/validation pipeline. Resolve a conflicting submission by an explicit preserved archive and evidence note, never last-write-wins.
3. Reconcile completed experiments to outcomes with originating search IDs. Prioritize actual result/verification debt over new policy machinery.
4. Update central capability/experiment/MASTER/queue/skills only when evidence changed; keep promotions small and reversible. No candidate promotions based solely on scores.
5. Check that generated plans contain concrete actions/domain anchors, current STOP gates, and useful protected exploration. A verifier without a frozen candidate is a hypothesis challenge, not post-discovery independent verification.
6. Check readiness/claim/telemetry gaps and stale packets. Do not infer learning success from files existing.
7. Report changed conclusions and remaining bottlenecks. Benchmark architecture superiority and realized commercial value require evidence, not system complexity.
