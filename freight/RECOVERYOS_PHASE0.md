# RecoveryOS Phase 0 — foundation complete

Status: implementation candidate on `feat/freight-phase0-recoveryos`.

This phase is the engineering foundation for the plan to make Freight Recovery
competitive with the strongest freight-audit platforms while preserving the
existing evidence-first financial truth model.

## Delivered

1. **Canonical freight schema**
   - immutable invoice/shipment records;
   - integer-cent money and integer physical measures;
   - source-artifact SHA-256 lineage;
   - canonical record hashes;
   - parcel package detail plus shared multi-mode shipment fields.

2. **Contract / rate authority compiler**
   - LTL and parcel authority terms;
   - effective-date and scope resolution;
   - precedence handling;
   - ambiguity fails closed;
   - human-verification state is part of the immutable authority hash.

3. **LTL + parcel rerating engine**
   - LTL CWT, minimums, discounts, lane/class factors, fuel and accessorials;
   - parcel actual/dimensional billable weight, zone/weight bands, fuel,
     residential and accessorials;
   - integer arithmetic only;
   - missing or ambiguous authority and unmapped charge semantics route to review;
   - unverified authority may calculate an estimate but cannot produce an
     auto-rated result.

4. **Human Reviewer Cockpit backend**
   - deterministic prioritization by materiality, uncertainty, novelty and
     downstream risk;
   - immutable case hashes;
   - explicit human decisions: CONFIRM, REJECT, NEED_EVIDENCE, MODIFY_RULE,
     ESCALATE;
   - corrected expected amounts and rule candidates are captured as review data,
     not silently promoted into production rules.

5. **Universal ingress envelope**
   - one proof-bound ingress surface for API, email, SFTP, portal, upload and
     batch sources;
   - transport identity is separated from file trust;
   - existing fail-closed CSV/XML/EDI/X12/PDF validation remains authoritative;
   - every accepted/rejected payload gets a SHA-256 receipt and downstream route.

6. **Benchmark harness**
   - deterministic replay check;
   - rated/review counts;
   - billed/expected/variance totals;
   - wall-clock throughput measurement;
   - stable benchmark hash excludes machine-dependent timing.

## Phase 0 acceptance boundary

Phase 0 does **not** claim production-scale integrations, OCR, universal contract
extraction, global-mode rating, banking rails, SOC 2/ISO certification or
competitor-beating scale. Those belong to later phases.

A human reviewer remains an intentional control. Machine output cannot convert
missing/ambiguous commercial authority into validated recovery.

## Remaining phases

- **Phase 1:** incumbent-challenge engine, enterprise adapters/API/SFTP/EDI,
  production customer-data plane, and modern analyst/client UX.
- **Phase 2:** payment orchestration plus TL/intermodal/air/ocean breadth and
  natural-language analytics.
- **Phase 3:** external assurance and scale proof: SOC 2/ISO program, external
  penetration testing, large-scale benchmarks, reliability evidence, and the
  continuously maintained competitor supremacy matrix.

There are **3 phases remaining after Phase 0**.
