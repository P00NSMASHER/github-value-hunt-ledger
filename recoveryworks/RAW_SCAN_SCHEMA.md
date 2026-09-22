# Raw Recovery Scan 360 schema

The raw-scan boundary accepts structured records only. It does not OCR source
documents, infer governing terms, or ask an LLM to calculate money.

Required root fields:

- `schema`: currently `1`
- `scan_id`: immutable operator-selected scan identifier
- `client_id`: one client only
- `selection_rule`: plain-language definition of the frozen population
- one or more branch blocks

Supported branch blocks:

- `ap`: verified invoice authority + posted payment records
- `utility`: effective-dated tariff + bill usage/demand records
- `payer`: exact procedure/date fee-schedule rates + paid service lines
- `duty`: exact effective-dated HTS rate + customs entry lines
- `construction`: reviewed entitlement evidence + optional required forensic schedule impact
- `freight`: existing FreightRecovery ChargeRule + InvoiceCharge inputs

Each load-bearing source must carry a source hash and locator. The raw pipeline
derives the branch-specific source manifest automatically, then the common scan
layer rejects any observation whose rule or evidence hash is outside that frozen
manifest.

A `verified: true` flag is not self-proving. It represents an upstream human or
controlled-system verification decision. RecoveryWorks preserves that decision
and will not promote unverified inputs to validated dollars.

Branch limitations remain explicit:

- PayerRecovery exact-rate engine does not silently model modifiers, bundling,
  capitation, multiple-procedure reductions, or contract terms that have not
  been implemented as explicit rules.
- DutyRecovery exact-rate engine excludes AD/CVD, quota, origin-program
  judgment, and HTS classification judgment unless separate verified modules
  are added.
- ConstructionRecovery does not make legal-entitlement judgments. A configured
  delay case can require a verified forensic schedule-impact artifact.
- FreightRecovery continues to use its existing deterministic charge-rule
  derivation engine and controlling-authority gate.
