# RETALLY App Factory source map

Evidence snapshot: **October 20, 2026**. The original sources for Supply Desk,
Renewal Desk, Client Intake, and the default estimating and inventory editions
have been located in `P00NSMASHER/x402-product-factory`. This closes the
implementation-location gap for the `app-factory-products` catalog entry.
It does not establish a private business identity, deployed service, release
readiness, buyer demand, customer count, or revenue.

## Source authority and lifecycle

The latest inspected application candidate is commit
`fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88`, branch
`factory/repair-watchdog-receipt-durability-20261015`, at PR #60. The observed PR
state was **open, draft, and unmerged**. Its [application source tree][candidate]
contains the recipes, three domain engines, packaging code, and acceptance code.
Treat the editions as **source-located draft local synthetic candidates**.

The inspected default `main` commit,
`27293158aeda848f2bc68ce2c5f6aca71b57cb44`, had no
`packages/application-factory` subtree. The complete recursive trees contained
390 entries on main and 805 on the candidate. Searching only the default branch
therefore missed these application sources. PR #58 merged main into the candidate
branch; it did not merge the application stack into main.

| Development point | Inspected commit | Original source evidence |
| --- | --- | --- |
| Initial three document-workflow prototypes, PR #25 | `05b599299c30ed2378d3aa8041d8a0a0b24cd84e` | [Original document recipes][D-original] |
| Complete local document-application packaging, PR #31 | `672380a33cfbec0be371a5e6c0b67e71f3021f5b` | [Original manufacturing contract][manufacturing-original] |
| Quote-to-order family, PR #40 | `d9bda57f6751333ad5fd929e910f20ba70d77d6d` | [Original quote recipes][Q-original] |
| Inventory-control family, PR #41 | `0e075681dd154d55afb246aef05589bf95aea0a0` | [Original inventory recipes][I-original] |
| Latest inspected cumulative candidate, PR #60 | `fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88` | [Current application tree][candidate] |

PRs #25, #31, #40, #41, and #60 were all open drafts at the snapshot. The table
records the observed source lineage; it does not authorize integration or release.

## Nine default editions

These are source-defined recipe editions of three shared engines. Count them as
application candidates, not nine independently operating businesses. Buyer scopes
below describe the recipes' intended workflows, not validated market demand.

| Edition | Canonical recipe ID | Family | Source-defined workflow | Current recipe |
| --- | --- | --- | --- | --- |
| Supply Desk | `supplier-desk` | `document-workflow` | Supplier records, required-document checklist, and renewal dates for small distributors | [D][D] |
| Renewal Desk | `contractor-renewals` | `document-workflow` | Contractor document expiry and renewal reminders for operations teams | [D][D] |
| Client Intake | `agency-intake` | `document-workflow` | Project brief, brand assets, and sign-off checklist for agencies | [D][D] |
| Print Estimate Desk | `print-estimate-desk` | `quote-to-order` | Itemized print production estimates and internal scheduling handoff | [Q][Q] |
| Rental Estimate Desk | `equipment-rental-estimates` | `quote-to-order` | Equipment-day estimates and internal dispatch review | [Q][Q] |
| Field Service Estimate Desk | `field-service-estimates` | `quote-to-order` | Maintenance labor and materials estimates with controlled work-order handoff | [Q][Q] |
| MRO Parts Replenishment | `mro-parts-replenishment` | `inventory-control` | Spare-parts availability and internal replenishment review | [I][I] |
| Rental Consumables Control | `rental-consumables` | `inventory-control` | Rental-preparation stock and internal refill requests | [I][I] |
| Hospitality Supply Desk | `hospitality-supply-desk` | `inventory-control` | Housekeeping stock and internal replenishment review | [I][I] |

The following recipe blobs are identical at their original family commit and the
latest inspected candidate. Commit pins identify the source context; Git blob
SHAs identify the exact files read.

| Ref | Path under the repository root | Git blob SHA |
| --- | --- | --- |
| D | `packages/application-factory/recipes.json` | `fd0135235c8644bc6be4f8b318181d0c38af924e` |
| Q | `packages/application-factory/quote-family/recipes.json` | `1638a532ccb321455eb167ed77d4f16d837e93ad` |
| I | `packages/application-factory/inventory-family/recipes.json` | `5eb317f4449d415e1d40de4ad57b52f336c71eec` |

## Three implemented engines

The inspected source includes domain logic and packaging code, not only product
descriptions. The [architecture contract][architecture] identifies three shared
workflow families. The [manufacturing contract][manufacturing] defines accepted
packages as local implementation-test results and explicitly separates those
results from commercial release.

| Family | Inspected implementation | Recipe-to-package binding |
| --- | --- | --- |
| Document workflow | [Durable runtime][document-runtime] with browser/API workflow, internal worker, evidence and recovery modules | [Assembler][document-assembler] uses an explicit source-file allowlist and the selected document recipe. |
| Quote to order | [Quote kernel][quote-kernel] implements integer-cent totals, quote states, independent review, and internal order handoff. | [Quote manufacturing][quote-manufacturing] packages kernel, store, server, browser UI, launch script, and recipe. |
| Inventory control | [Inventory engine][inventory-engine] implements stock, reservations, consumption, replenishment suggestions, and internal approval. | [Inventory manufacturing][inventory-manufacturing] packages engine, store, server, browser UI, launch script, and recipe. |

The packaging implementations declare `releaseApproved:false`,
`realCustomers:null`, and `collectedRevenue:null`. These are source-declared
candidate boundaries, not measurements of a live service. No deployment,
customer, payment, or revenue claim is inferred from source presence.

## Subordinate hypotheses and identity boundaries

The [cross-family proposal registry][proposals] contains **14 additional workflow
hypotheses**, seven quote workflows and seven inventory workflows. It has kind
`cross-family-hypothesis-queue`; each entry has
`sourceStatus:"background_only_unverified"`. Its Git blob SHA is
`e162d01cfcb27af34c2dd7b0aa5a807b0ab5b146`. The [proposal compiler][proposal-compiler]
derives recipes from those inputs. These records belong beneath the application
family as hypotheses/variants. They do not establish 14 additional businesses or
independent buyer validation. The nine defaults plus fourteen hypotheses also
do not establish 23 independent backends.

| Similar name or shared location | Required distinction |
| --- | --- |
| Supply Desk / Hospitality Supply Desk | `supplier-desk` is supplier document intake. `hospitality-supply-desk` is housekeeping inventory control. Preserve both recipe IDs. |
| Renewal Desk / Contractor Quote Recovery | `contractor-renewals` tracks contractor documentation. None of the nine default recipes establishes an alias or source binding to the separate Contractor Quote Recovery venture. |
| Estimating tools / Contractor Quote Recovery | Quote-to-order editions calculate estimates and manage internal approval/handoff. Do not substitute them for a separately sourced quote-recovery experiment. |
| App Factory products / x402 API services | The [numbered API registry][x402-registry] is a separate product family in the same repository. Repository sharing does not merge product identities, customers, or financial attribution. |
| App Factory products / shared Software Factory infrastructure | The [AI Business OS Software Factory contract][software-factory] governs engineering work and approval lifecycle. It is not the original application recipe source or an additional customer product. |

## Observed CI metadata and verification limits

GitHub returned **11 completed-success check runs** for the exact candidate SHA
`fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88`, completed on October 20 between
14:45:43 and 14:47:49 UTC. The check names were `integrated-release-source`,
`Check pinned draft PR ancestry and exact-head CI (not release approval)`,
`test`, `quote-apps`, `candidate-build`, `inventory`, `pilot`, `remote-preview`,
`acquisition`, `browser`, and `manufacturing`.

Evidence: [exact-head check metadata][checks],
[manufacturing run][ci-manufacturing], [quote run][ci-quotes],
[inventory run][ci-inventory], and [browser run][ci-browser]. Run links identify
fixed GitHub run IDs; the check endpoint is anchored to the inspected commit.
The success counts are an observation at this snapshot, not a permanent status.

This source-recovery review read repository files and GitHub metadata. It did
not rerun the application tests, inspect a downloaded generated package, verify
a live deployment, or access customer, contact, or payment payloads. CI success
does not close release, market-validation, or operational-identity questions.
Keep source recovery separate from those remaining evidence requirements.

[candidate]: https://github.com/P00NSMASHER/x402-product-factory/tree/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory
[D-original]: https://github.com/P00NSMASHER/x402-product-factory/blob/05b599299c30ed2378d3aa8041d8a0a0b24cd84e/packages/application-factory/recipes.json
[Q-original]: https://github.com/P00NSMASHER/x402-product-factory/blob/d9bda57f6751333ad5fd929e910f20ba70d77d6d/packages/application-factory/quote-family/recipes.json
[I-original]: https://github.com/P00NSMASHER/x402-product-factory/blob/0e075681dd154d55afb246aef05589bf95aea0a0/packages/application-factory/inventory-family/recipes.json
[D]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/recipes.json
[Q]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/quote-family/recipes.json
[I]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/inventory-family/recipes.json
[manufacturing-original]: https://github.com/P00NSMASHER/x402-product-factory/blob/672380a33cfbec0be371a5e6c0b67e71f3021f5b/packages/application-factory/manufacturing/README.md
[manufacturing]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/manufacturing/README.md
[architecture]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/ARCHITECTURE.md
[document-runtime]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/runtime/runtime.js
[document-assembler]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/manufacturing/assembler.js
[quote-kernel]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/quote-family/kernel.js
[quote-manufacturing]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/quote-family/manufacturing.js
[inventory-engine]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/inventory-family/engine.js
[inventory-manufacturing]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/inventory-family/manufacturing.js
[proposals]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/autonomy/cross-family/proposals.json
[proposal-compiler]: https://github.com/P00NSMASHER/x402-product-factory/blob/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/packages/application-factory/autonomy/cross-family.js
[x402-registry]: https://github.com/P00NSMASHER/x402-product-factory/blob/27293158aeda848f2bc68ce2c5f6aca71b57cb44/product-registry.json
[software-factory]: https://github.com/P00NSMASHER/github-value-hunt-ledger/blob/04252c375e8abf8564dd42a5fd5524bf6635a4fa/ai_business_os/SOFTWARE_FACTORY_CONTRACT.md
[checks]: https://api.github.com/repos/P00NSMASHER/x402-product-factory/commits/fc5ccb3ee3e31a7bfdb47a74d700b978efec2b88/check-runs?per_page=100
[ci-manufacturing]: https://github.com/P00NSMASHER/x402-product-factory/actions/runs/39442153040
[ci-quotes]: https://github.com/P00NSMASHER/x402-product-factory/actions/runs/39442153568
[ci-inventory]: https://github.com/P00NSMASHER/x402-product-factory/actions/runs/39442153456
[ci-browser]: https://github.com/P00NSMASHER/x402-product-factory/actions/runs/39442153069
