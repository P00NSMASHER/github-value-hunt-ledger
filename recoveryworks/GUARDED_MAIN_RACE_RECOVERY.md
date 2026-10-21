# RETALLY generated PR race recovery — bounded merged-tree proof

**Status: implementation candidate; new recovery path has mocked/offline tests but has not yet passed a live provider-backed race.** The owner-authorized Scout and Integrator writer PR paths already passed real five-lane exact-source CI and fully automated normal merges. Catalog PR #550 passed the exact-source five-lane gate but `main` advanced during CI because of an unrelated Oracle source correction; the fail-closed bot controller stopped, and the owner manually reconciled and merged the one synthetic file after inspecting disjoint paths and test evidence.

## Only-one-proof recovery contract

1. Authenticate the bot-authored, non-draft, same-repo source PR with its original frozen head, original single-parent base and strict generated file allowlist. Never rewrite, rebase or force-push that bot proposal.
2. When current `main` changed, require a linear, small delta (at most twelve commits, fewer than two hundred file records), with no overlap to the proposal or its input dependencies. Any `.github/`, `tools/`, `tests/` change, or a change to any file writable by that lane is a HOLD. Technology Intelligence also blocks **every** concurrent `intelligence/` update.
3. Create exactly one unique `automation/retally-proof-<trusted-run-id>-<attempt>` GitHub branch at the verified current `main` SHA. Merge the frozen bot proposal head into **that branch only** using GitHub's normal non-force merge API. Refuse unknown merge parents, unexpected changed files, malformed SHA, branch collision or GitHub provider uncertainty.
4. Run a new full `Repository Release Gate` via explicit `workflow_dispatch` on the **proof merge SHA**, not on the original outdated proposal. Require all five lanes to PASS and bind the run's event, branch, commit and creation time. A single shared CI retry budget expires before the original 30-minute GitHub job limit.
5. Recheck original bot PR lineage and immutable source, current main still exactly the proof parent, and then call GitHub's ordinary, SHA-locked PR merge. Verify the resulting main commit **tree SHA matches the CI-proven proof tree**. Any mismatch is a material integrity incident: keep customer production HOLD and do not claim a completed proof.
6. Only one proof branch and one proof-CI run per original controller invocation. If `main` advances again, file scope widens, CI fails, or a GitHub operation is rejected, do not retry recursively. Preserve source PR, proof branch and logs for bounded reconciliation.

No administrator bypass, human reviewer gate, external customer claims, OCI operation, new paid service, public network access or release authorization is introduced. The checked-in `main` ruleset remains **disabled** until all four writer lanes are verified to behave correctly without direct pushes.

## Evidence / rollout

- **Prior real failure:** Catalog bot PR #550, single synthetic `lanes/` file, all five source CI lanes PASS; unrelated OCI correction advanced main before bot merge, correctly triggering HOLD. It was reconciled by owner-authorized normal GitHub merge without force. This was **not** a successful automatic race recovery.
- **Current candidate:** seven new adversarial/offline tests plus the existing guarded-controller suites, including wrong proof parents, changed main, wrong file scope, non-linear source history and bounded CI timeout. PAAM-L044 ran 25 targeted tests PASS at exact candidate commit.
- **Provider acceptance still required:** a future safe synthetic race test or naturally occurring disjoint advance should prove the branch-proof API and final identical tree. Do not state live race recovery success on the basis of mocks alone.

**Customer production release: HOLD.**
