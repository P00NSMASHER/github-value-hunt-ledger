# RecoveryOS Blind Audit Acceptance Protocol v2

Version: 2.0  
Effective: 2026-10-07  
Machine policy: `freight/AUDIT_ACCEPTANCE_POLICY_V2.json`  
Validator/report engine: `freight/audit_acceptance.py`

## Purpose

This protocol defines the minimum methodology required before RecoveryOS may
describe a real buyer population as **AUDIT_QUALITY_PROVEN**.

It is intentionally stricter than the internal synthetic gold benchmark. The
synthetic benchmark proves deterministic conformance of encoded logic. This
protocol tests whether RecoveryOS remains accurate and economically honest on a
messy, buyer-authorized, independently adjudicated population.

Passing this protocol still does not establish realized recovery, enterprise
security certification, universal accuracy, or performance outside the frozen
population.

## 1. Pre-register the study before RecoveryOS output exists

Before the sample is run, freeze:

1. buyer entity and business unit;
2. full population definition and SHA-256;
3. sampling method;
4. strata;
5. random seed when sampling;
6. target sample counts by stratum;
7. truth owner;
8. two independent reviewer identities;
9. RecoveryOS operator identity;
10. incumbent-output source and freeze procedure;
11. acceptance policy version;
12. source completeness and authority rules.

The validator requires the truth owner, two reviewers, and RecoveryOS operator
to be distinct roles.

## 2. Sampling

Use one of two methods only:

### CENSUS

Every item in every declared stratum is included.

### STRATIFIED_RANDOM

Freeze a random seed before RecoveryOS output exists. Strata must be defined
from buyer-operational facts available before outcomes are known.

Recommended stratification dimensions are:

- freight mode;
- carrier;
- spend/charge band;
- business unit or facility where material;
- document/source type where extraction quality may differ.

Do not build strata from RecoveryOS findings, dollar variance, confidence,
review status, or any other post-model outcome.

Every declared stratum has:

- population count;
- sample target;
- observed sample count.

Missing a target fails the methodology gate.

The policy also calculates a conservative 95% finite-population sample-size
requirement using the worst-case binomial variance (p=0.5) and the configured
margin-of-error target. The current target is +/-5 percentage points. A complete
small-population census can therefore satisfy the design without an arbitrary
200-case ritual, while a 10,000-item population requires 370 sampled cases
before the precision-planning gate passes.

For disproportionate stratified samples, the report applies each stratum's
design weight (population count / sampled count). Raw sample metrics remain
visible, but population-weighted precision, false-positive rate,
false-negative rate, coverage, review rate and dollar metrics are reported and
gated separately.

## 3. Four independently frozen evidence objects

The pilot retains separate hashes for:

1. the buyer-authorized population;
2. the selected sample IDs;
3. the independently adjudicated truth manifest;
4. the frozen RecoveryOS output.

The incumbent output is separately hashed as well.

The validator recomputes the sample, truth, and RecoveryOS-output hashes from
case-level data. A one-cent truth or model-output edit after freeze is therefore
detectable.

## 4. Blindness ordering

The minimum timing contract is:

1. population frozen;
2. sample selected;
3. RecoveryOS output frozen without access to truth;
4. incumbent output frozen;
5. independent truth adjudication frozen without access to RecoveryOS;
6. joint unseal;
7. comparison and scoring.

Steps 3-5 may occur in parallel, but both sides remain sealed until joint
unseal.

The protocol records five explicit blindness assertions:

- truth owner did not see RecoveryOS output before truth freeze;
- RecoveryOS team did not see truth before output freeze;
- sample was selected before RecoveryOS output;
- the dual-review subset was selected before RecoveryOS output;
- truth owner is independent of the RecoveryOS builder.

A violation makes the study **INVALID_METHOD**, not merely a failed accuracy
test.

## 5. Truth states

Truth is not forced into a binary answer when reality does not support one.

Each case is:

- `POSITIVE`: supportable overcharge/recovery opportunity exists;
- `NEGATIVE`: no supportable positive discrepancy exists;
- `UNRESOLVED`: available evidence cannot support either conclusion.

Each case also records:

- truth variance in integer cents;
- authority state;
- source completeness;
- economic issue identity;
- whether the incumbent already knew the issue.

Unresolved authority or incomplete source evidence is not converted to a
negative truth label merely to make metrics easier.

Semantic invariants are machine-enforced:

- POSITIVE truth requires positive truth variance;
- NEGATIVE truth requires zero truth variance;
- unresolved authority or incomplete source evidence requires UNRESOLVED truth.

## 6. RecoveryOS states

RecoveryOS returns one of:

- `POSITIVE`;
- `NEGATIVE`;
- `REVIEW`.

`REVIEW` is an abstention. It is not silently counted as a correct
auto-decision.

Each output records:

- predicted variance in integer cents for automatic decisions;
- confidence in parts per million;
- claimed net-new candidate cents.

Output semantics are also enforced:

- POSITIVE automatic decisions require positive predicted variance;
- NEGATIVE automatic decisions require zero predicted variance;
- REVIEW carries no asserted variance;
- non-POSITIVE decisions cannot assert net-new cents;
- net-new cents cannot exceed the predicted variance.

An automatic positive or negative on unresolved truth, unresolved authority, or
incomplete evidence is an **unsupported auto-decision**. The acceptance policy
allows zero.

## 7. Dual-review truth quality

At least the greater of:

- 50 cases; or
- 20% of adjudicated cases

must be independently labeled by two reviewers.

The report computes:

- raw agreement;
- Cohen's kappa.

Current acceptance requires:

- at least 10 dual-reviewed positive-truth cases;
- at least 10 dual-reviewed negative-truth cases;
- kappa >= 0.70.

This prevents a degenerate all-positive or all-negative agreement sample from
passing merely because both reviewers repeated the same label.

Every reviewer disagreement requires a documented adjudication note. The truth
owner may preserve `UNRESOLVED`; adjudication is not permission to manufacture
certainty.

## 8. Statistical uncertainty

Point estimates alone are prohibited for the primary case-error metrics.

The report uses 95% Wilson intervals for:

- positive precision;
- false-positive case rate;
- false-negative case rate.

Current acceptance thresholds include:

- finite-population sample size sufficient for the +/-5 point 95% planning target;
- >= 200 adjudicated cases when the population itself contains at least 200 items;
- >= 30 positive cases;
- >= 30 negative cases;
- precision 95% lower bound >= 0.85;
- false-positive-rate 95% upper bound <= 0.12;
- false-negative-rate 95% upper bound <= 0.12.

These are acceptance thresholds for the bounded pilot, not a promise that the
true production rates equal the limits.

## 9. Selective-classifier / abstention metrics

The report separately exposes:

- auto-decision coverage;
- review/abstention rate;
- automatic-decision accuracy.

Current minimum auto coverage is 60%; maximum review rate is 50%.

This prevents a system from claiming excellent accuracy merely by sending nearly
everything to a human.

## 10. Dollar-weighted error

Case counts alone can hide economically catastrophic errors.

The report therefore calculates:

- false-positive dollars;
- false-negative dollars;
- false-positive dollar share;
- false-negative dollar share;
- automatic-decision mean absolute dollar error;
- automatic net dollar bias;
- exact-dollar rate;
- truth-positive dollars routed to review.

Current acceptance requires:

- false-positive dollar share <= 1%;
- false-negative dollar share <= 5%.

A single large miss can therefore fail the gate even when ordinary case
accuracy remains visually impressive.

## 11. Confidence calibration

For automatic decisions, confidence is compared with observed correctness in
ten bins.

The report emits:

- expected calibration error (ECE);
- Brier score;
- per-bin count, average confidence, and accuracy.

Current acceptance requires ECE <= 0.10.

Confidence is therefore measured rather than treated as decorative decimal
places emitted by a model.

## 12. Incumbent and duplicate protection

The report separately measures:

- net-new cents credited to issues the incumbent already knew;
- duplicate net-new cents credited more than once to one economic issue.

Current acceptance requires both to be exactly zero.

This is a hard commercial invariant. A statistically accurate audit can still
be commercially wrong if it bills the buyer for incumbent-known or duplicated
value.

## 13. Stratum-level reporting

Every declared stratum reports:

- population count;
- sample count;
- adjudicated count;
- false positives;
- false negatives;
- review count.

The first pilot report must show these tables even when the overall gate passes.
A strong aggregate may not conceal one failing mode, carrier, source type, or
spend band.

When strata are sampled at different fractions, the report also exposes the
population-weighted aggregate. This prevents an oversampled rare stratum from
quietly becoming the buyer-wide error rate.

## 14. Gate states

### INVALID_METHOD

The study design or frozen evidence contract is invalid, including blindness,
hash, role-separation, sampling, timestamp, or adjudication failures.

Do not publish accuracy metrics as blind validation.

### INSUFFICIENT_EVIDENCE

The method is valid, but sample precision, event prevalence, balanced
dual-review coverage, or declared stratum coverage is insufficient to support
the full quality claim.

This is not a product failure. It means the study cannot answer the question
with the required strength.

### QUALITY_GATE_FAILED

The method is valid and enough evidence exists to evaluate at least the
applicable quality/integrity gates, but one or more product-quality gates fail.

Unsupported automatic decisions, incumbent-known net-new leakage, or duplicate
net-new leakage are hard integrity failures even in a smaller sample.

### AUDIT_QUALITY_PROVEN

Every v2 methodology and acceptance gate passes.

This status is scoped only to the exact frozen buyer population and protocol.

It is not `REALIZED_RECOVERY_PROVEN`.

## 15. Recovery remains a separate proof chain

After audit-quality acceptance:

validated finding
-> buyer authorization
-> carrier/vendor action
-> independently observed settlement/credit/remittance
-> reversal observation
-> uniquely attributable realized value
-> fee eligibility

No accuracy metric, confidence interval, reviewer decision, submitted dispute,
or promised credit skips that chain.

## 16. Permanent anti-gaming rule

Any future methodology revision must preserve or strengthen:

- independent truth ownership;
- blind ordering;
- immutable hashes;
- unresolved truth;
- stratification;
- confidence intervals;
- dual-review agreement;
- abstention disclosure;
- dollar-weighted error;
- calibration;
- incumbent-known exclusion;
- duplicate suppression;
- separate settlement proof.

A methodology change that removes one of those controls requires an explicit
version increase and must not inherit the v2 acceptance claim.
