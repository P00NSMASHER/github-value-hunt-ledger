# RecoveryOS hostile-examination protocol

This protocol defines the minimum reproducibility package for a high-value
RecoveryWorks finding. It is designed for adversarial internal, customer,
counterparty, auditor, expert, or counsel review.

It does **not** establish legal entitlement by itself and does not authorize
external action. Existing human-review and explicit customer-authorization gates
remain mandatory.

## Threat model

Assume an examiner challenges all of the following:

- the authority/rule was altered or superseded;
- source evidence was edited after ingestion;
- the analyst selected favorable records and omitted contrary records;
- the money calculation cannot be reproduced;
- a hidden adjustment changed the result;
- a different code version or input population was used later;
- reviewer timestamps or approvals were backfilled;
- the lifecycle journal was modified after approval;
- the case packet was assembled from mismatched components;
- an outbound amount differs from the validated/authorized amount.

RecoveryOS should fail closed when one of these bindings is broken.

## Seven-figure minimum controls

A finding at or above `SEVEN_FIGURE_CENTS` requires:

1. a VALIDATED finding with verified controlling rule and evidence;
2. a point-in-time AuthoritySnapshot bound to the exact rule source hash,
   locator, and effective dates;
3. one authenticated SourceAttestation for every load-bearing evidence item;
4. a CalculationManifest binding calculator identity/version, code commit,
   input manifest, expected/actual/recovery amounts, and deterministic trace hash;
5. at least two distinct approving reviewers;
6. a resolved adversarial challenge review by a reviewer independent of all
   approving reviewers;
7. an explicit deadline assessment;
8. a frozen CaseProofBundle;
9. exact raw-artifact replay of authority and evidence bytes;
10. independent calculation replay of the frozen amounts and trace;
11. a replayable durable-ledger journal head;
12. a detached proof seal over the frozen case and journal head;
13. a signed HostileExaminationPacket binding the replay receipts and proof seal;
14. a source-retention manifest proving every load-bearing authority/evidence
    object has a retained custody record and, for high-value cases, a verified
    immutable-storage/object-lock attestation;
15. a case-completeness manifest reconciling the frozen source population and
    documenting resolved negative/contrary-evidence searches;
16. a build-provenance attestation binding the calculator identity/version and
    code commit to a specific CI/build run, source tree, dependency lock, build
    artifact, and passing tests; and
17. a privacy-preserving public verification record containing only hashes and a
    Merkle root, so a published timestamped record can later prove the private
    case components have not changed.

## Independent examination procedure

### Step 1 — Verify the frozen case

Run `verify_case_bundle(bundle)`.

This rechecks:
- finding proof hash
- authority binding
- source-attestation coverage
- calculation binding
- reviewer independence
- challenge resolution
- deadline presence
- chronology
- bundle hash

### Step 2 — Replay original source bytes

Provide the exact authority artifact and exactly one artifact per evidence ID to
`replay_case_source_artifacts(...)`.

The replay fails if:
- the authority bytes hash differently;
- any evidence bytes hash differently;
- an evidence artifact is missing;
- an undeclared artifact is added;
- replay is dated before the frozen case.

The resulting `CaseArtifactReplayReceipt` is content-addressed.

### Step 3 — Independently reperform the calculation

Using the frozen calculator identity/version, code commit, and input manifest,
recompute expected and actual amounts and produce the exact deterministic trace
bytes.

Pass those values to `replay_case_calculation(...)`.

The replay fails if any of these differ:
- calculator ID
- calculator version
- code commit
- input manifest hash
- expected amount
- actual amount
- derived recovery amount
- calculation trace hash

Calculation replay must occur after source-artifact replay.

### Step 4 — Replay the lifecycle journal

Export the durable ledger and reconstruct it with
`DurableRecoveryLedger.from_bundle(...)`.

The reconstructed journal head must exactly match the original head hash.

### Step 5 — Verify detached proof seal

Use `verify_proof_seal(...)` with the configured verification key/KMS path and
the replayed journal head.

The proof seal binds:
- frozen case bundle
- finding proof
- durable journal head
- optionally authorization
- optionally outbound action envelope

### Step 6 — Verify the hostile-examination packet

Run `verify_hostile_examination_packet(...)`.

The signed packet binds:
- case bundle hash
- finding proof hash
- raw-artifact replay receipt hash
- calculation replay receipt hash
- proof seal ID/signature
- journal head
- assembly actor/time

Any change to the bound component set invalidates verification.

## Simulation fixture

The repository includes synthetic seven-figure FreightRecovery data and tests.
The simulation is not customer evidence and must never be represented as a real
recovery.

The simulated finding is exactly USD 1,000,000:

- expected: USD 4,250,000
- actual: USD 5,250,000
- variance: USD 1,000,000

The hostile-examination tests deliberately attack:

- authority bytes
- evidence bytes
- missing/extra artifacts
- calculation expected amount
- calculation trace
- code commit identity
- journal head
- packet contents
- signing key
- replay chronology

## Production acceptance criteria

Before treating a seven-figure finding as examination-ready:

- raw source bytes are retained in immutable/private storage;
- source hashes in the frozen case match those bytes;
- code commit exists in the controlled repository;
- calculation trace is deterministic and retained;
- reviewers are identifiable and independent as required;
- negative/contrary evidence search is documented;
- deadlines are reviewed by an appropriate human;
- the durable ledger exports and replays without mismatch;
- replay receipts verify;
- proof seal verifies through the production key-management process;
- hostile-examination packet verifies;
- no external action occurs before explicit customer authorization.

## Current cryptographic posture

The reference implementation uses HMAC-SHA256 for detached proof seals and
hostile-examination packet signatures. Production deployments should execute the
sign/verify operation using a controlled KMS/HSM key rather than exposing key
material to application code or case files.

A later hardening increment may add asymmetric/public-verification signatures,
external timestamping, WORM/object-lock retention, and independent build
attestations.


## Custody, completeness, and build provenance

### Immutable/private retention

Use `freeze_source_retention(...)` to create one custody record for the
controlling authority and every load-bearing evidence item.

For a retained object to be marked `immutable_storage_verified=true`,
RecoveryOS requires:

- a retention mode;
- a retention control/object-lock identifier; and
- a provider attestation hash.

RecoveryOS does not infer immutability from a storage URI or bucket name.
The retention timestamp may not predate source acquisition and may not postdate
the retention manifest.

Production deployments should verify provider/object-store retention state
against the actual storage API and retain that provider attestation privately.

### Source-population completeness

Use `freeze_case_completeness(...)`.

Each PopulationSegment records:

- frozen source-export hash;
- explicit selection rule;
- full record count;
- included count;
- excluded count;
- control-total hash;
- included-ID hash; and
- excluded-ID hash.

Included plus excluded counts must equal the full population count.

The manifest also requires one or more resolved NegativeEvidenceSearch records.
These make the search for amendments, credits, reversals, waivers, exclusions,
rebills, and other contrary facts explicit instead of treating absence of
contrary evidence as an unstated assumption.

### Build provenance

Use `create_build_provenance_attestation(...)`.

The attestation binds the frozen case calculator to:

- calculator ID/version;
- exact code commit;
- repository;
- build system;
- workflow identity/run ID;
- dependency-lock hash;
- source-tree hash;
- build-artifact hash;
- passing-test state; and
- build/attestation timestamps.

A high-value build attestation cannot be created with failed tests.

### Public transparency record

Use `create_public_verification_record(...)` only after the private controls
above exist.

The public record contains no source locators or source bytes. It publishes
hash-only identifiers for:

- case bundle;
- finding proof;
- hostile-examination packet;
- retention manifest;
- completeness manifest;
- build attestation; and
- journal head.

A deterministic Merkle root binds those leaves.

This public record provides privacy-preserving transparency and later
change-detection. It does **not** by itself authenticate RecoveryWorks as the
publisher. Production should publish/sign the record through an external
asymmetric-signature or transparency/timestamp service. RecoveryOS deliberately
does not implement home-grown public-key cryptography in this reference layer.
