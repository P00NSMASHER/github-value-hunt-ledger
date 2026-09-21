# Coordination protocol

Purpose: let the 14 research workers and Hunt 15 integrator exchange high-information learning without racing on one shared mutable file or forcing every hunter to reread the full ledger.

This protocol applies only after a worker's frozen benchmark duty is complete. Shadow workers keep their shadow write restrictions and may reference this protocol only when their shadow contract permits the same information to stay inside shadow-authorized paths.

## Design

Each materially useful live run may emit exactly one immutable coordination packet at:

`intelligence/coordination_spool/<safe-run-id>.json`

The packet is a handoff index, not the evidence store. Detailed evidence remains in the hunter catalog/referral and the canonical search-run record remains in `search_run_spool/`.

Workers never replace another worker's packet. Hunt 15 owns the compact view in `intelligence/COORDINATION_BOARD.md`.

## Signal types

Use only signals that can change another worker's next action:

- `capability_delta` — a real new/strengthened capability or implementation identity.
- `negative_knowledge` — a reusable failed proof obligation, dominated pattern, false-positive signature or dead end.
- `referral` — an exact cross-lane question another worker is better positioned to answer.
- `contradiction` — evidence that weakens an existing capability, experiment, score, assumption or candidate.
- `search_lesson` — a LOCAL method lesson with scope, evidence and failure mode; never a global skill promotion.
- `next_test` — the cheapest falsifiable action that would materially change the conclusion.

Do not emit a signal just because a repository was found. A packet with zero signals is valid when no cross-hunter learning occurred.

## Packet contract

Required top-level fields:
- `schema_version`: 1
- `packet_id`: stable unique `COORD:...`
- `source_run_id`: canonical/prospective run ID when available; null only for clearly unallocated live work
- `source_hunter`: `HUNTER-XX`
- `created_at`: UTC timestamp
- `signals`: array, normally 0-5 items

Each signal should contain:
- `signal_id`: stable unique `SIG:...`
- `type`: one of the six signal types above
- `subject`: concise repository@revision, CAP/EXP ID, or exact technical subject
- `dedupe_key`: normalized identity for the claim/question, not prose-only wording
- `capability_ids`, `experiment_ids`
- `target_worker_ids` and/or `target_lane_ids` when known
- `priority`: low | normal | high | blocking
- `question`: exact unanswered question for referrals/next tests, otherwise null
- `failed_proof_obligation`: exact reason a candidate/claim failed when applicable
- `evidence_refs`: durable paths/URLs/revisions needed to reconstruct the handoff
- `expires_at`: optional; use only for genuinely time-sensitive signals

Never include credentials, private/personal data, confidential material, leaked trade secrets, exploit instructions or unauthorized-access material.

## Producer rules

Before emitting:
1. deduplicate against the relevant current board entry when practical;
2. prefer one precise signal over several overlapping summaries;
3. separate a candidate-specific rejection from a task-wide no-find;
4. preserve exact revision and evidence boundary;
5. route the unresolved proof obligation, not a vague "please investigate";
6. do not claim another worker accepted or completed a referral without readback.

The source run may list emitted IDs in `coordination_signal_ids`.

## Consumer rules

Before substantial duplicate work, read only board entries relevant to the current assignment/capability/experiment.

A board item is context, not truth:
- reverify load-bearing evidence;
- respect current domain STOP gates and live leases;
- do not treat a referral as a claim or promotion;
- do not inherit another worker's score, verifier status or commercial conclusion without the underlying evidence.

## Hunt 15 reconciliation

After benchmark scoring duty and canonical run intake:
1. read new immutable coordination packets;
2. reject malformed/sensitive/duplicate packets without deleting them;
3. merge unresolved high-information signals into `COORDINATION_BOARD.md`;
4. close/supersede signals only with a concrete evidence reference or current central state;
5. route durable negative knowledge to `REJECTED.md`, capability deltas to capability/graph state, experiment changes to `EXPERIMENTS.md`/queue, and eligible LOCAL lessons to the existing skill-verification path;
6. preserve provenance from board entry -> packet -> run -> detailed evidence;
7. keep the board compact: unresolved actionable signals, not historical narrative.

## Learning policy

Coordination volume is not a KPI. Track whether signals:
- prevented duplicate deep inspection;
- produced a retained/verified candidate;
- exposed a contradiction earlier;
- closed an experiment gap;
- caused a useful negative result;
- shortened the path to a real outcome.

Do not let coordination-derived routing affect automatic allocation until there is enough measured evidence to show it improves useful outcomes without increasing recall failures.
