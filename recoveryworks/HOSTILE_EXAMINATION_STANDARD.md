# RecoveryOS hostile-examination standard

This standard defines the minimum proof/control package for a RecoveryWorks
finding that may be challenged by a sophisticated counterparty, auditor,
customer, expert, regulator, or court.

The first hard gate applies automatically at **$1,000,000 of validated
potential recovery** (`100,000,000` cents). Lower-value cases may use the same
controls voluntarily.

This standard is about trustworthy evidence and controlled action. It does not
declare that a customer is legally entitled to money, replace branch-specific
professional judgment, or authorize RecoveryWorks to contact a counterparty.

## Seven-figure invariant

A seven-figure finding may not move through the ordinary single-review
authorization path.

Before external action, RecoveryOS requires all of the following:

1. a VALIDATED deterministic finding;
2. one verified controlling rule;
3. a point-in-time authority snapshot that exactly binds to that rule;
4. authenticated source attestations for every load-bearing evidence item;
5. a calculation manifest that binds the finding to calculator/version,
   code commit, input manifest, and calculation trace;
6. two distinct approving RecoveryWorks reviewers;
7. a resolved adversarial challenge review by a reviewer independent of the
   approving reviewers;
8. an explicit deadline assessment, including an explicit
   "no deadline identified" conclusion where applicable;
9. a frozen content-addressed CaseProofBundle;
10. explicit client authorization by an actor independent of RecoveryWorks
    reviewers;
11. an exact outbound artifact hash and immutable locator;
12. a content-addressed ExternalActionEnvelope binding the artifact to the
    frozen case and client authorization;
13. a detached proof seal binding the frozen case, authorization, external
    action, and durable-journal head to a KMS/HSM-managed key.

The ledger rejects a seven-figure case that attempts to bypass these controls.

## 1. Authority Registry

`AuthoritySnapshot` represents the exact authority used by the calculation.

Required fields include:

- authority ID and type;
- source SHA-256/content hash;
- exact source locator;
- effective dates;
- acquisition timestamp;
- human verifier and verification note;
- jurisdiction where relevant;
- explicit supersession link where relevant.

`AuthorityRegistry` is content-addressed. Reusing an authority ID with
different content is rejected. The registry export has its own deterministic
hash and verifies every embedded snapshot when reloaded.

A frozen case must bind the controlling `RuleRef` to exactly the same:

- source hash;
- source locator;
- effective-from date;
- effective-to date;
- jurisdiction when both sides specify one.

A document filename or rule label is not authority provenance.

## 2. Source authentication

A source hash proves which bytes were processed. It does not prove that those
bytes are authentic.

Every load-bearing `EvidenceRef` in a frozen case therefore requires one
`SourceAttestation` recording:

- evidence ID;
- exact source hash and locator;
- acquisition method;
- acquisition time;
- person/system that authenticated the source;
- authentication note;
- verification state.

Examples of stronger acquisition methods include counterparty portals,
read-only APIs, bank/ERP exports, executed-contract repositories, and other
independently controlled systems.

The actual source object should remain in an immutable/private evidence vault.
RecoveryOS stores its hash and locator in the proof packet.

## 3. Reproducible calculation

Every frozen case requires a `CalculationManifest` containing:

- calculator ID;
- calculator version;
- code commit SHA;
- frozen input-manifest hash;
- finding proof hash;
- expected amount;
- actual amount;
- potential recovery;
- calculation-trace hash;
- creation timestamp.

The manifest is rejected if any amount or finding hash differs from the frozen
finding.

The purpose is to answer:

> Which code, which inputs, and which calculation trace produced this dollar
> amount?

An LLM extraction result is never a substitute for this deterministic manifest.

## 4. Independent review and adverse evidence

Seven-figure cases require two distinct approving reviewers.

They also require a separate `ChallengeReview` whose reviewer is independent
of both approving reviewers. The challenge must be resolved before the case can
freeze.

The challenge question should be adversarial, for example:

- Is there a superseding amendment?
- Was the amount already credited?
- Is a rebill/reversal missing?
- Is there a contrary shipment/meter/usage fact?
- Is the wrong payer/product/contract hierarchy being used?
- Does a waiver, exclusion, cap, rider, or deadline defeat the case?

RecoveryOS preserves the challenge conclusion and hashes of contrary-evidence
search artifacts.

## 5. Deadline assessment

Every seven-figure case requires a `DeadlineAssessment`.

It records:

- governing source hash and locator;
- trigger event;
- assessment timestamp;
- assessor;
- deadline timestamp when one exists;
- conclusion.

If no material deadline is identified, that conclusion must be explicit rather
than represented by missing data.

The external-action gate rejects an action prepared after an assessed deadline.

## 5A. Temporal consistency

For a hostile-examination case, chronology is part of the proof.

RecoveryOS rejects a case when:

- calculation time predates acquisition of the authority or any load-bearing
  source;
- a reviewer, challenge reviewer, or deadline assessor claims to have reviewed
  a calculation before that calculation existed;
- a review/assessment postdates the frozen case it is supposedly inside;
- client authorization predates the frozen case;
- an outbound action predates client authorization;
- an authorization expiry predates the authorization itself; or
- a final proof seal predates the case/action it claims to bind.

This prevents a technically hash-consistent packet from containing impossible
or backfilled chronology.

## 6. Frozen CaseProofBundle

`freeze_case_proof(...)` creates the content-addressed proof packet.

The bundle contains:

- full immutable finding payload;
- authority snapshot;
- source attestations;
- calculation manifest;
- review attestations;
- adversarial challenge reviews;
- deadline assessments;
- optional Recovery Scan batch hash;
- creator and timestamp;
- deterministic bundle hash.

Reloading or modifying any covered field changes the proof and causes
verification failure.

This is the unit that should be exported for hostile examination.

## 7. Client authorization

`authorize_case_action(...)` binds explicit client approval to one frozen case
bundle and one finding proof.

It records:

- authorization ID;
- frozen case hash;
- finding proof hash;
- client actor ID;
- approved action type;
- authorization time;
- maximum authorized amount;
- note;
- optional expiry.

The client actor may not be one of the approving or adversarial RecoveryWorks
reviewers.

A seven-figure ledger record cannot use the legacy
`ledger.authorize(finding_id, authorization_id)` route. It must use
`authorize_with_case(...)`.

## 8. Exact external-action artifact

Before a seven-figure finding can enter CLAIMED state, RecoveryOS requires an
`ExternalActionEnvelope`.

It binds:

- CaseProofBundle hash;
- client authorization hash and ID;
- finding ID and proof hash;
- approved action type;
- exact outbound artifact SHA-256;
- immutable artifact locator;
- artifact byte length;
- action amount;
- preparer and preparation timestamp.

Changing even one byte of the outbound artifact makes
`verify_external_action(..., artifact_bytes=...)` fail.

The ledger records the external-action envelope hash.

This allows an examiner to distinguish:

- what RecoveryWorks calculated;
- what reviewers approved;
- what the customer authorized; and
- what RecoveryWorks actually prepared/sent.

## 9. Durable lifecycle replay

`DurableRecoveryLedger` journals:

- ADD;
- primary APPROVE;
- INDEPENDENT_APPROVE;
- AUTHORIZE_CASE with the complete frozen case and client authorization;
- CLAIM with the external-action envelope;
- RECOVER/REJECT outcomes.

The existing journal hash chain therefore covers the seven-figure proof packet
and action gate. A durable bundle can be replayed into the same logical state,
and tampered journal payloads fail verification.

## 9A. Detached proof seal

A final seven-figure packet may be sealed with `ProofSeal`.

The seal binds:

- frozen case bundle hash;
- finding proof hash;
- client authorization hash when present;
- external-action envelope hash when present;
- durable journal head hash;
- seal time;
- key identifier.

The current code uses HMAC-SHA256 so it has no additional runtime dependency.
The secret is never stored in the proof packet. A production deployment should
perform the HMAC with a KMS/HSM-managed key and retain the provider audit trail
for the key operation. The in-repo simulator uses an explicitly synthetic key
only for regression testing.

The proof seal is intentionally detached: the case remains independently
content-addressed, while the seal demonstrates that a trusted key-holder
attested to the exact frozen state.

## 10. Separation of duties

For a seven-figure case, the minimum distinct identities are:

- primary reviewer;
- independent approving reviewer;
- adversarial/challenge reviewer;
- client authorizer.

The challenge reviewer must be independent of the approving reviewers, and the
client authorizer must be independent of RecoveryWorks reviewers.

Deployments should additionally restrict authority publication, rule-pack
deployment, and outbound-action execution by role/IAM policy. The code-level
proof model is necessary but does not replace infrastructure access controls.

## 11. Hostile-examination questions the packet must answer

A complete case should allow an independent examiner to answer:

1. What exact transaction/claim is at issue?
2. What rule governed at that time?
3. Where did that rule come from?
4. Which original sources support the material facts?
5. How were those sources authenticated?
6. Were contradictory facts searched for and resolved?
7. Which exact code and inputs produced the amount?
8. Can the finding be reproduced?
9. Who reviewed it?
10. Who independently challenged it?
11. What deadline/dispute window was considered?
12. Who at the customer authorized external action?
13. What exact artifact was prepared/sent?
14. Was that artifact changed after approval?
15. What response and recovered cash ultimately occurred?

If the platform cannot answer one of those questions, the case is not ready for
a seven-figure external assertion.

## Step 1 acceptance criteria

Step 1 is complete when CI proves:

- Authority Registry export/reload detects tampering.
- Seven-figure case freezing rejects a single reviewer.
- Seven-figure case freezing rejects unresolved/non-independent challenge review.
- Authority/rule mismatches fail.
- Calculation/finding mismatches fail.
- Every load-bearing evidence item requires source authentication.
- Legacy high-value authorization is blocked.
- High-value authorization requires independent ledger approval and a frozen
  proof bundle.
- High-value CLAIMED transition requires an external-action envelope.
- A one-byte artifact change fails verification.
- Durable journal export/replay preserves the frozen case hash, authorization
  hash, and outbound-action envelope hash.
- Impossible chronology (review before calculation, authorization before
  freeze, action before authorization) is rejected.
- Rehashed action envelopes cannot change the authorized action type or exceed
  the validated recovery amount.
- A detached proof seal fails under the wrong key or journal head and cannot
  predate the action it binds.
- The synthetic seven-figure fixture completes the full proof lifecycle and is
  explicitly labeled simulation-only.
- Existing lower-value RecoveryWorks lifecycles remain backward compatible.
