# Freight Recovery v15 — Canonical Release Manifest

Release checkpoint: **v15-commercialization-2026-09-20**

## Source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Merged source commit: `1c55081543c332497e288a8a8129acf8c0588191`
- Pull request: **#7 — Freight Recovery v15: commercialization model, pilot gate, rights registry, and workflow hardening**
- PR head tested: `320efa01c2cb45ab5fe7d0d8b2403b258907d657`
- CI run: `35517699090`
- CI job: `test`
- Result: **success**

## CI integrity at this checkpoint

Pinned GitHub Actions:
- `actions/checkout@11d5960a326750d5838078e36cf38b85af677262`
- `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`

Pinned test dependency file:
- `production/requirements-ci.txt`

Test command:
```bash
cd production && python -m pytest -q test_prototype.py
```

Important: this CI validates the committed hunter-system production contracts and the workflow hardening touched by PR #7. It is **not** evidence that a full multi-tenant Freight Recovery SaaS runtime has been deployed.

## Canonical v15 commercial control files

- `freight/BUSINESS_MODEL.md`
- `freight/PILOT_PROTOCOL.md`
- `freight/COMPONENT_RIGHTS_REGISTRY.json`
- `freight/RELEASE_AND_SECURITY_GATE.md`
- `freight/ROADMAP.md`
- `COMBINATIONS.md` — Freight Recovery v15 stack
- `EXPERIMENTS.md` — EXP-001 commercial proof gate
- `OPPORTUNITIES.md` — paid wedge / pricing / ICP
- `SEARCH_QUEUE.md` — freight commercialization freeze

## Commercial state

Freight Recovery v15 is **commercially specified and diligence-hardened, but EXP-001 remains BLOCKED_EXTERNAL**.

The product has not yet proven:
- a paid customer blind audit;
- a challenger-only incumbent miss on a frozen customer population;
- a customer-approved dispute/action that reached a carrier/vendor credit/refund/remittance;
- an unambiguous realized-recovery allocation;
- conversion to annual continuous assurance.

These remain the highest-value evidence gaps.

## Rights state

The operational rights record is `freight/COMPONENT_RIGHTS_REGISTRY.json`.

The registry intentionally distinguishes:
- public repository license;
- user-asserted separate commercial permission;
- unknown assignment/change-of-control/sublicensing/hosted-SaaS rights;
- separately governed third-party data, standards, vendor services, trademarks, patents and customer records.

Do not infer transferability from commercial-use permission.

## Security state

PR #7 materially improved repository supply-chain safety by:
- pinning external GitHub Actions to immutable full SHAs;
- restricting catalog/integrator write helpers to allowlisted paths;
- rejecting absolute/path-traversal destinations;
- adding concurrency/timeouts;
- making the production-contract test job read-only;
- pinning Python CI dependency versions.

Still required before continuous enterprise assurance:
- isolated customer data/control plane;
- tenant/BU negative tests;
- parser isolation and hostile-input limits;
- independent verifier identity;
- immutable/versioned evidence store;
- SBOM + signed artifact/provenance;
- retention/deletion/export policy;
- incident-response runbook;
- backup/restore evidence.

## Commercial model

Initial offer ladder:
1. **$5k–$7.5k** Data Readiness / Authority Diagnostic.
2. **$15k–$25k** Blind Freight Audit Acceptance Test.
3. **15–20%** of uniquely attributable realized credit/refund/cash only.
4. After proof, initial **$60k–$150k annual assurance**, with larger multi-BU deployments **$150k–$300k+** depending on complexity.

No fee-eligible recovery may be created from unsupported authority, incumbent-preidentified findings, automatic/preexisting credits, duplicate recovery or ambiguous settlement.

## Next canonical milestone

The next release should be cut only after one of these materially changes:
- EXP-001 begins on an authorized customer population;
- a required pilot/security control is implemented;
- a customer exposes a concrete integration/capability gap;
- a rights/transferability status is resolved.

Broad freight feature/repository accumulation alone is not a reason to create a new major version.
