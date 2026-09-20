# Freight Recovery v15 — Commercial Operating Model

Updated: 2026-09-20

## Positioning

Freight Recovery is **not** another TMS and should not be sold as generic AI invoice audit.

The first product is an **Independent Freight Audit Acceptance Test**:

> Freeze the customer's commercial authority and shipment truth, independently reproduce expected charges, compare the result blind against the incumbent audit/payment process, and call a dollar recovered only after an attributable credit/refund/remittance is proven.

The product's commercial moat is the proof chain:
**authority -> expected charge -> observed invoice -> evidence sufficiency -> incumbent comparison -> dispute/action -> settlement**.

## Initial ICP

Prioritize a shipper or 3PL that meets most of these conditions:
- roughly $5M+ annual transportation spend or 500+ freight invoices/month;
- multiple carriers and meaningful accessorial exposure;
- an incumbent TMS, AP, freight-payment or audit process already exists;
- contracts/rate confirmations/addenda/tariffs can be supplied for a frozen historical population;
- shipment truth can be supplied (BOL/POD/appointments/weight/telematics when relevant);
- incumbent findings can remain unopened until buyer-owned truth is frozen;
- later credit/refund/remittance evidence can be supplied.

Do not start with a customer that cannot provide controlling commercial authority or eventual settlement evidence. That creates analysis work, not defensible recovery proof.

## Offer ladder

### 1. Data Readiness / Authority Diagnostic
- Price: **$5,000–$7,500 fixed**.
- Machine gate: `freight/readiness.py` produces BLOCKED / CONDITIONAL / READY; a high numeric score can never override authorization, blind-order, authority, identity, retention, or settlement-observability blockers.
- Purpose: determine whether the buyer has enough source authority, shipment evidence and settlement data for a blind acceptance test.
- Credit: may be credited against a full pilot if started within the agreed period.
- Deliverable: source inventory, unresolved-authority report, normalization plan and pilot-ready population definition.

### 2. Blind Freight Audit Acceptance Test
- Price: **$15,000–$25,000 fixed** for a defined frozen historical population.
- Clock starts only after the data-readiness gate passes.
- Target turnaround after complete inputs: **10–15 business days** for the analysis/report portion.
- Deliverables:
  - frozen-population manifest/hash;
  - frozen buyer-owned truth manifest;
  - independently reproduced expected charges;
  - REVIEW vs validated findings;
  - blind incumbent comparison;
  - source-linked dispute/review packets;
  - explicit false-positive-dollar and reviewer-touch metrics.

### 3. Managed Recovery
- Price: **15–20% of uniquely attributable realized credit/refund/cash**.
- Never charge on:
  - incumbent-preidentified findings;
  - automatic/preexisting credits;
  - unresolved settlement allocation;
  - unsupported authority;
  - duplicate recovery;
  - estimated or "potential" savings.
- "Realized" means a later customer-controlled settlement source proves the amount and allocation.

### 4. Continuous Freight Assurance
- Initial mid-market target: **$60,000–$150,000 annual base**.
- Larger multi-BU / enterprise target: **$150,000–$300,000+ annual base**, normally with a lower incremental-recovery percentage.
- Price against audited spend, invoice/population complexity, source count, carrier/mode complexity and integration burden—not seats.

## Commercial qualification and margin gate

Use `freight/deal_economics.py` before quoting delivery scope.

- The diagnostic or pilot must meet the target gross margin on its **fixed fee alone**.
- Default internal planning target: **50% fixed-fee gross margin** until real delivery data justify changing it.
- Do not use expected recovery, success-fee upside, or speculative customer savings to make an otherwise unprofitable engagement look viable.
- Loaded analyst cost, other delivery costs, and analyst-hour budget must be explicit before work starts.
- `max_analyst_hours_at_target_margin` is the delivery budget. If the expected work exceeds it, narrow scope, raise fixed fee, improve process efficiency, or HOLD the deal.
- The $5M annual-spend / 500-invoice threshold is a prioritization signal, not an automatic rejection. A smaller buyer can proceed if readiness, complexity, strategic value and fixed-fee economics are sound.
- One-carrier / low-complexity populations are flagged because they may offer less differentiation, but margin and proof quality remain the hard gates.

Success fees remain optional upside after settlement proof; they are never part of the qualification math.

## Expansion sequence

1. Paid data-readiness diagnostic.
2. Paid blind acceptance test.
3. One settlement-proven unique incumbent miss.
4. Managed recovery on the same evidence model.
5. Annual shadow/continuous assurance.
6. Only then add integrations repeatedly demanded by paying customers.
7. Broader "freight financial control plane" positioning comes after repeatable customer proof.

## Commercial invariants

- Discrepancy dollars are not recovery dollars.
- Model confidence is never commercial authority.
- Missing/ambiguous controlling authority = REVIEW / $0.
- Missing/ambiguous shipment identity = REVIEW / $0.
- Missing required physical/document evidence = REVIEW / $0.
- Ambiguous settlement allocation = $0 realized.
- A component never validates itself.
- The incumbent output stays sealed until buyer-owned truth is frozen.
- Customer data is read-only during the first pilot unless a separately approved workflow says otherwise.

## KPI hierarchy

### Commercial
- paid pilots signed;
- diagnostic -> pilot conversion;
- pilot -> annual conversion;
- annual contract value;
- days complete data -> first defensible finding;
- days complete data -> final pilot report;
- realized recovery / validated recovery;
- uniquely attributable realized dollars;
- customer concentration;
- gross margin.

### Integrity
- unsupported asserted dollars: **$0**;
- unsupported realized dollars: **$0**;
- population drift after freeze: **0**;
- duplicate recovery certificates: **0**;
- same-component self-validation accepted: **0**;
- assertions with exact authority/evidence lineage: **100%**;
- realized recovery with settlement provenance: **100%**;
- deterministic replay on frozen cases: **100%**.

## Stop rules

For the next 60–90 days:
- stop broad freight feature hunting;
- do not build another TMS/rating/OCR/rules layer;
- do not add self-service UI that is not required by a paid pilot;
- do not widen to new modes/verticals without a customer-triggered gap;
- new repository hunting is allowed only when EXP-001 exposes a named missing capability or connector.

The highest-value milestone is not another code module. It is:
**paid blind pilot -> unique incumbent miss -> issued credit/refund -> unambiguous settlement -> recovery certificate -> annual contract**.
