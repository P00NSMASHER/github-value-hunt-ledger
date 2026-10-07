# RecoveryOS Phase 3 — Step 3 Accuracy & Financial Integrity

Status: **COMPLETE AS AN INTERNAL SYNTHETIC GOLD BENCHMARK / EXTERNAL BLIND CUSTOMER VALIDATION PENDING**  
Completed internally: 2026-10-07

Step 3 asks a different question from Step 2. Performance tells us whether the
software can repeat its work quickly. Accuracy asks whether the work is correct.

The answer is encouraging, but narrower than a brochure writer would prefer.

## 1. Frozen gold set

RecoveryOS now has a frozen, hash-bound synthetic gold fixture:

- gold id: `recoveryos-phase3-accuracy-v1`;
- fixture SHA-256:
  `6da44c566a8e7d495b2e7fce80508529fa598232077b690f60c4b1804b2274a7`;
- benchmark report SHA-256:
  `83f642e4448a0c17735efdcb046325ce50a08728298084dc981db3df0fd57ecd`;
- source workflow run: **37575308610**;
- source job: **112642756810**;
- source commit: `4880899058bd71b0f0f38cbc56886df261bc3ba4`.

The fixture contains **42 explicit scenarios**:

- 20 rating/financial-state cases;
- 4 controlling-authority resolution cases;
- 8 incumbent-attribution cases;
- 10 PaymentOS lifecycle cases.

All six supported modes are represented:

- Parcel;
- LTL;
- TL;
- Intermodal;
- Air;
- Ocean.

The expected answer is stored in the fixture before runtime execution. The
benchmark compares RecoveryOS output against those frozen expectations and the
CI validator rejects an altered fixture/report hash.

## 2. Rating accuracy

The 20 rating cases include positive overcharges, correctly rated negatives and
expected fail-closed reviews.

Auto-rateable cases: **13**.  
Expected review cases: **7**.

Classification results:

- true positives: **7**;
- true negatives: **6**;
- false positives: **0**;
- false negatives: **0**;
- auto-rateable abstentions: **0**.

Synthetic gold metrics:

- precision: **100%**;
- recall: **100%**;
- specificity: **100%**;
- automatic classification accuracy: **100%**;
- expected-review routing accuracy: **100%**;
- exact expected-charge accuracy: **100%**;
- exact variance accuracy: **100%**;
- exact financial-state accuracy: **100%**;
- authority binding on the rating cases: **100%**.

The review cases deliberately exercise missing parcel zone, missing LTL class,
missing TL mileage, missing intermodal chassis days, missing air dimensions,
missing ocean container type and an unverified controlling authority. RecoveryOS
did not convert any of those missing facts into invented money.

## 3. Controlling-authority selection

Four independent resolution scenarios exercise:

- higher-priority authority wins;
- newest applicable effective-date authority wins;
- equal-precedence conflicting authorities fail as **AMBIGUOUS**;
- absent authority fails as **MISSING**.

Exact authority-resolution conformance: **4/4 (100%)**.

This is important because perfect arithmetic under the wrong contract is still a
wrong invoice. Freight software occasionally forgets that rather inconvenient
detail.

## 4. Second-look attribution and duplicate suppression

Eight frozen challenger/incumbent scenarios exercise:

- incumbent-known finding;
- automatic credit;
- already-open claim;
- genuine challenger-only candidate;
- zero-positive-variance suppression;
- blocked/review case;
- duplicate challenger economic identity.

Exact attribution conformance: **8/8 (100%)**.

The frozen batch expected and observed:

- challenger-only candidate: **3,000 cents**;
- incumbent-known candidate variance: **1,700 cents**;
- review-routed candidate variance: **4,200 cents**;
- suppressed positive variance: **0 cents**.

Duplicate-suppression accuracy: **100%**.  
Incumbent-credit protection accuracy: **100%**.

That means the gold set never awarded RecoveryOS net-new credit for a frozen
incumbent-known matter and did not double-count the duplicate challenger pair.

## 5. Payment financial-state integrity

Ten PaymentOS cases cover:

Valid states:

1. PREPARED;
2. AUTHORIZED;
3. SUBMITTED;
4. ACCEPTED;
5. SETTLED;
6. REVERSED;
7. FAILED.

Invalid cases:

- provider submission without human authorization;
- illegal PREPARED/AUTHORIZED -> SETTLED state jump;
- provider amount different from the authorized instruction.

Results:

- valid state + money accuracy: **7/7 (100%)**;
- invalid lifecycle rejection: **3/3 (100%)**;
- only SETTLED reports settled cents;
- REVERSED returns settled cents to zero;
- deterministic payment replay verification passes.

This prevents a prepared payment, an authorization, or a provider acknowledgement
from quietly becoming "money recovered."

## 6. Evidence genealogy

The benchmark checks hash/provenance continuity for rating results, incumbent
attribution outputs and payment lifecycle outputs.

Traceable outputs: **38/38**.  
Synthetic traceability accuracy: **100%**.

This verifies the encoded evidence links and hashes in these scenarios. It does
not prove an outside source document was truthful. Cryptography can prove that a
bad document was not changed; it cannot make the bad document wise.

## 7. Mutation tests

The benchmark suite also deliberately corrupts expected answers.

CI verifies that it rejects:

- a one-cent change to expected rating variance;
- a changed net-new attribution amount;
- a changed expected settled payment amount;
- replacement of the frozen fixture hash.

This matters because a "gold benchmark" that silently changes its gold whenever
the implementation changes is merely unit testing in an expensive hat.

## 8. The critical limitation

**The 100% result is not a production accuracy estimate.**

It would be irresponsible to advertise "0% false positives" or "100% accuracy"
based on this fixture.

Why:

- only 13 cases are auto-rateable;
- the cases are synthetic and deliberately constructed;
- the expected results are code-adjacent rather than independently adjudicated
  from messy customer evidence;
- no OCR/document extraction error is present;
- no real negotiated contract prose or amendment ambiguity is represented;
- no carrier portal behavior is represented;
- no real invoice-feed corruption or identity-resolution mess is represented;
- no external settlement source is represented;
- unsupported freight rules are not discovered merely by passing supported
  rules.

The correct claim is:

> **RecoveryOS achieved exact conformance on the frozen internal synthetic gold
> set, including zero synthetic false positives/false negatives and exact
> financial-state accounting. Real-world false-positive and false-negative rates
> remain unproven.**

## 9. What external proof is still required

Production accuracy needs a buyer-authorized **blind frozen population** in which
the truth labels are adjudicated independently of RecoveryOS output.

At minimum, the external benchmark must measure:

- invoice/shipment coverage;
- authority-selection accuracy;
- supported-rule coverage;
- false positives;
- false negatives discovered by independent review;
- exact-dollar error;
- review-abstention rate;
- incumbent-known suppression;
- duplicate economic-issue suppression;
- net-new attributable candidate dollars;
- authorized claims;
- settled/reversed outcomes;
- actual net recovered dollars;
- reviewer minutes per 1,000 invoices.

RecoveryOS output must remain hidden from the adjudicator until the truth set is
frozen. Otherwise the benchmark becomes self-grading, a proud old human
tradition.

External blind validation status:

**PENDING_EXTERNAL_CUSTOMER_EVIDENCE**

## 10. Permanent regression gate

The repository now contains:

- `freight/fixtures/phase3_accuracy_gold_v1.json`;
- `freight/accuracy_benchmark.py`;
- `freight/accuracy_evidence.py`;
- `freight/PHASE3_ACCURACY_BASELINE.json`;
- `freight/test_phase3_accuracy.py`;
- dedicated `RecoveryOS Phase 3 Accuracy` CI.

The gate freezes both the fixture hash and exact report hash. A code or fixture
change that alters any expected classification, dollar amount, authority,
attribution, payment state or traceability metric fails until the accuracy
baseline is deliberately reviewed.

## Step 3 verdict

**RecoveryOS now has strong internal evidence that its encoded financial logic is
deterministic, fail-closed and exactly correct on the frozen 42-scenario
synthetic corpus.**

That is materially better than having no formal accuracy harness.

It is still weaker than a blind customer benchmark, and pretending otherwise
would undermine the evidence discipline that is supposed to be the product's
advantage.

Step 3 is therefore complete internally, with the external customer-proof
portion explicitly carried forward rather than fabricated.
