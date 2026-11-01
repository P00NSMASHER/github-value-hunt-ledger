# RETALLY | Competitor source code and independent product proof

**Captured:** October 12, 2026. **Decision:** No evidence supports claiming RETALLY is the best full-service freight-audit/payment product. This page does not claim access to proprietary production repositories. The objective is to measure audited performance rather than overinterpret public code or marketing.

## GitHub source reality (five primary incumbents)

| Company | Accessible source/technical interface | What it does **not** establish |
| --- | --- | --- |
| Trax Technologies | Public GitHub organization: https://github.com/TraxTechnologies . A dated MIT-licensed X12 parser: https://github.com/TraxTechnologies/scala-x12 . Public freight features: https://www.traxtech.com/products/freight-audit | This does not reveal the live Trax audit/rating engine or prove the public parser runs in production. |
| Loop | Developer repos https://github.com/loop-payments/prisma-safety and https://github.com/loop-payments/prisma-lint ; **official** API https://docs.loop.com/openapi ; ingestion architecture https://docs.loop.com/how-loop-works/artifact-ingestion | Engineering tooling is not DUX 2.0 production audit algorithms. API contracts describe interfaces, not correctness. |
| Intelligent Audit | Official product requirements: https://www.intelligentaudit.com/products/farbi | A similarly named open-source project is not the company's core freight platform. No authenticated backend source is established. |
| Cass Information Systems | Official service: https://www.cassinfo.com/freight-audit-payment and rating: https://www.cassinfo.com/freight-audit-payment/services/freight-rating | No publicly verified production core GitHub source; unrelated user projects bearing "Cass" are not ownership evidence. |
| nVision Global | Official service: https://corporate.nvisionglobal.com/freight-audit/ | No verified proprietary rating/reconciliation source. |

**Availability boundary:** Only public code or repositories to which the source owner legitimately grants access can be inspected. Private account visibility and permission to study/reuse private source are separate. Even public source without a license is not automatically reusable. Do not bypass authentication or publish third-party confidential documents.

## Observed product gap, not a ranking by code count

- Loop's published API exposes artifact preprocessing/categorization, derivative artifacts, shipment and payable invoice assignment, state transitions and business exceptions.
- Intelligent Audit markets 150+ audit points, automated claims and SKU-level general-ledger allocation.
- nVision advertises three freight rating engines, broad invoice capture, cross-region payments and ERP integrations.
- Cass reports enterprise payment and invoice scale. Scale and banking rails cannot be inferred from a public open-source parser.
- Trax markets global mode/currency coverage and enterprise data exchange.
- RETALLY's public code includes canonical hash-bound freight records, six-mode rating, incumbent-second-look attribution, payment-event controls, human review and a **42-scenario synthetic** conformance benchmark. It does not establish the same field-tested breadth, banking rails or buyer-validated recovered dollars.

**Benchmark comparability:** Loop's September 1, 2026 *vendor-published* AuditBench reports 94.8% on production LTL audit cases and 65% on challenge cases: https://www.loop.com/article/introducing-the-long-horizon-auditbench-for-supply-chain-ai . RETALLY's 100% on a separate small synthetic designed gold set must **not** be put on the same scoreboard. Neither product has been tested against the other's dataset here.

RETALLY's October 7 evidence-weighted, partly vendor-claim-based 14-dimension internal matrix rates RecoveryOS **56/100**, versus **82.8–85.6/100** for five incumbents. This is not independently measured production accuracy. The snapshot is useful for gap prioritization, not definitive buyer results.

## The defensible way to compare products

1. Use **one buyer-authorized, independently adjudicated, pre-registered frozen population**, following the existing freight/AUDIT_ACCEPTANCE_PROTOCOL_V2.md and freight/AUDIT_ACCEPTANCE_POLICY_V2.json. Separate buyer truth, reviewers, incumbent output and operator roles.
2. Run RETALLY and every participating product on **the identical blinded invoice/contract/receipt population**. Vendor trial access must be authorized by the operator. Never send confidential data without customer authorization.
3. Obtain **frozen case-level output exports and source receipts** from each participating vendor or licensed sandbox, including overcharge decision, amount in integer cents and review/abstention status. Confirm the vendor identity and data source independently.
4. Score each using RETALLY's existing Protocol-v2 engine. freight/vendor_head_to_head.py adds a strict equal-study check and side-by-side aggregates: exact amount correctness, false positives/negatives, abstentions, incumbent-known leakage and acceptance status.
5. If a vendor cannot be tested, label **NOT_OBSERVED**. Never assign zero accuracy or infer lack of functionality from hidden source. No synthetic/frozen-dataset result establishes universal #1 product status.
6. Validate separate dimensions: real buyer-owned recovered dollars (not candidate balances), supported modes and contract variations, invoice extraction, ERP/TMS integration, external security assurance, scale, actual SLA, cost and operational support.

### Usage

Provide a local, private JSON object with schema_version 1, study_kind SYNTHETIC or BUYER_AUTHORIZED_BLIND, and a submissions array of up to six objects. Each submission requires vendor, source_kind, output_receipt_sha256 and a valid full pilot payload conforming to Protocol v2.

Supported vendor names: RecoveryOS, Intelligent Audit, Trax, Cass Information Systems, Loop, nVision Global. Valid source_kind: SYNTHETIC_TEST, AUTHORIZED_VENDOR_EXPORT, AUTHORIZED_VENDOR_DEMO.

Evaluate **locally in an approved confidential workspace**, not public CI with customer data:

    python -m freight.vendor_head_to_head --study /secure-local-path/study.json

The default policy is freight/AUDIT_ACCEPTANCE_POLICY_V2.json. CLI output contains **aggregate statistics only**, not invoice IDs or case-level payloads. User-supplied hashes and labels do **not** prove independent authentication; a separate human source-evidence review is still required. No vendor products are contacted or executed by the comparison script.

### Release gate

The comparison is read-only: no credentials, customer data, production API calls, payments, carrier disputes, or production release changes. Synthetic tests are engineering checks, **not empirical proof that RETALLY wins**. This is a draft research and benchmark increment.

**Highest-value next experiment:** One buyer-authorized second-look population containing frozen prior-auditor output and independently reviewed outcomes. RETALLY's differentiated hypothesis is *net-new recovery beyond an incumbent*, not matching global bank-backed payment networks today.
