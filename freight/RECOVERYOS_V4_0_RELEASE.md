# RecoveryOS 4.0 | Live authenticated proof-ladder upgrade

**Status:** Published to the existing Floot app `https://freight-recoveryos.floot.app` on October 31, 2026.

## Version mapping

- Product/application version: **4.0.0**
- Previous internally completed program: RecoveryOS Phase 3 (October 7, 2026).
- Hosting and source of operational truth: Floot project `c719b60c-9b3b-4193-a543-0be9d3ceaef2`, published version `1793464725836`.
- Reversible prepublish checkpoint: `01c8dd1e-b05a-4da0-a9dc-1370bc894e0f`.
- Public Freight Recovery product version **16.0** is an independent version line, with different customer release gates.

## Delivered change

The authenticated RecoveryOS control room now includes a **Proof Ladder 4.0** view. It reads only the user's existing tenant-scoped dashboard aggregates and payment-instruction GET response. It distinguishes:

1. Reviewed source records (not proven overcharges);
2. Candidate differences and potential findings (not recovered money);
3. Human-confirmed findings (not independent carrier or bank settlement);
4. Payment instructions and marked authorizations (not provider acceptance or settlement);
5. Provider-reported payment labels (not bank-cleared proof);
6. Independent bank-cleared recovered cash (**UNAVAILABLE** from these APIs, never guessed).

The aggregate summary is copied only after an explicit action. It contains no case IDs, payer IDs, customer names or payment references. No new mutation endpoint, customer onboarding, carrier message, payment event, credential, schema or permission changed.

## Verified provider evidence

- Floot production publish job `ec67287c-a767-4848-9e88-2b6a30066177`: **succeeded**.
- Full application TypeScript typecheck: **clean**.
- 16 Floot Jasmine spec files: **16 passed, 0 failed**.
- New fail-closed proof-ladder spec: handles duplicate/invalid amounts, contradictory aggregate counts, provider-reported reversals and zero payments. Never treats a `SETTLED` provider label as bank-cleared cash.
- Authentication remains through the existing `UserRoute`; the new view has no public API route.

## Remaining external operational acceptance

Independent customer evidence, a legally authorized engagement, confirmed controlling tariffs, carrier adjudication, verified cleared payments/reversals, live protected storage and restore/retention controls and external assurance are separate obligations. **The Floot publish and code tests do not clear these external gates.** External action and customer production release remain **HOLD**.

## Floot publish diagnostic

Floot reported three existing endpoint integration warnings: `auth/microsoft_login_authorize_GET`, `recovery/import_POST`, and `recovery/payment_event_POST` have no in-app page caller. Some are intentionally external-facing or disabled. This version does not alter those endpoints; classify and document their legitimate external/disabled usage before any follow-on cleanup. Never connect a payment-event endpoint merely to silence a warning.
