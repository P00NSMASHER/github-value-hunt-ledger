# Hunt 08 R11 — SECS/GEM differential: atomicity correction and next discriminating probe

Date: 2026-09-20
Lane: Node 08 — Protocol Moats
Related capability/experiment: CAP-014 / EXP-008 / RAD-007

## Hypothesis tested
Prior static hypothesis: for an S2F15 batch `[valid first, invalid second]`, `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6` would reject atomically while `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f` might partially apply the first item.

## Independent verifier verdict
**FALSIFIED.** Both pinned implementations intentionally validate the whole batch before mutation. The prior predicted divergence came from an incomplete source-path read and must not be used as an incompatibility claim.

### Dreamine evidence — TESTED
- `GemEquipmentConstantService.SetValues` materializes the batch, rejects duplicate ECIDs before state mutation, validates each staged item under the state lock, and only then applies all values.
- The E30 equipment router routes S2F15 into that service and maps `Duplicate` to a distinct failure acknowledgement.
- The TCP loopback suite already executes the adversarial mixed batch: ECID 5 is initially 10; the host sends valid `5 -> 50` followed by unknown `6 -> 1`; the batch is rejected and a subsequent read verifies ECID 5 is still 10.

Evidence label: **IMPLEMENTED + SEMANTIC TCP-LOOPBACK TESTED**.

### secsgem evidence — IMPLEMENTED, mixed-invalid batch not directly regression-tested
- `equipment_constants_capability.py` performs a first pass across every S2F15 element to detect unknown IDs and min/max violations.
- Only when aggregate EAC remains success does a second pass call `_set_ec_value` for the batch.
- Tests cover a two-valid-item update and individual unknown/out-of-range rejection, but no explicit mixed valid+invalid batch test was found.

Evidence label: **IMPLEMENTED; supporting tests for multi-valid and individual invalid cases; mixed-valid+invalid atomicity test NOT FOUND**.

## Important new predicted disagreement: `EC-DUPLICATE-PROBE`
A higher-information static divergence is now visible.

Test vector: send one S2F15 containing the same valid ECID twice with two individually valid values, e.g. `[ECID 5 -> 40, ECID 5 -> 50]`, after freezing the starting value.

Predicted Dreamine result:
- Detect duplicate ECID in the staged batch using a `HashSet`.
- Reject with its duplicate-status acknowledgement.
- Apply neither update; post-state remains the pre-request value.

Predicted secsgem result:
- First validation pass sees both entries as independently valid; no duplicate check is present in the inspected handler.
- Second mutation pass applies both entries in order.
- Return success EAC; post-state becomes the second value.

This is **SOURCE-PREDICTED, NOT RUNTIME-CONFIRMED**. Neither implementation is treated as the standards authority if they disagree. The value is that this probe cleanly distinguishes transaction semantics with a machine-readable post-state.

## Remote-command timing re-check
A second suspected disagreement was also weakened by deeper inspection. secsgem explicitly sends S2F42 with `ACK_FINISH_LATER` before invoking the remote-command callback, then emits the configured completion collection event after callback completion. Its tests assert S2F42 `ACK_FINISH_LATER` before the Stream-6 event. Dreamine's loopback path likewise separates accepted S2F42 from the later command-completion event. Therefore remote-command acknowledgement/completion ordering should currently be treated as an expected-convergence case, not the highest-priority predicted disagreement.

## Runtime status
Cross-engine execution was **NOT_RUN** in this automation environment: repository/network materialization is unavailable in the local runtime and the Python `secsgem` package is not preinstalled. No runtime disagreement is claimed.

## Negative knowledge
1. Do not infer partial mutation from a loop until the complete validation -> mutation path is traced; both engines use separate validation and apply phases.
2. Do not promote an unexecuted source prediction into an incompatibility finding.
3. Differential-corpus cases should be classified before execution as either **expected convergence invariant** or **predicted disagreement probe**, then judged on observable acknowledgement + post-state.
4. The original mixed-valid/invalid `EC-ATOMIC-PROBE` remains useful, but as a convergence/guardrail case.

## Experiment impact
- Keep mixed valid+invalid S2F15 in the frozen corpus as an atomic-rejection invariant.
- Add `EC-DUPLICATE-PROBE` as the next highest-information differential case.
- Record both reply code and read-back state; do not interpret reply-only differences as semantic incompatibility without state evidence.
- Use the third independent SECS/GEM engine only if the two pinned engines actually disagree at runtime.

## Commercial impact
This correction strengthens the proposed **SECS/GEM Pre-FAT Differential Regression** wedge because it reduces false-positive incompatibility reports. The product should explicitly distinguish:
- invariant checks where independent engines are expected to converge;
- discriminating probes where source analysis predicts divergent semantics;
- unresolved disagreements that require standards/customer-authority review.

## Search-policy lesson candidate
**VALIDATE-PASS -> MUTATE-PASS TRACE**
When testing transactional protocol semantics, trace all validation passes, mutation passes, duplicate/ordering rules, acknowledgement mapping, and post-state tests before predicting partial application. Turn any surviving semantic difference into a minimal duplicate/order/invalid-element perturbation probe.

Status: candidate lesson only; do not promote to SEARCH_SKILLS.md until independently successful on another distinct task or approved by Hunt 15.

## Next highest-value question
Does `EC-DUPLICATE-PROBE` reproduce the source-predicted divergence — Dreamine rejects duplicate ECIDs with no state change while secsgem accepts the batch and leaves the second value — when executed against both pinned revisions?
