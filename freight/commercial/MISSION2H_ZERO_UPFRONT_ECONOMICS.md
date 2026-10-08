# RETALLY | Mission 2H zero-upfront founding-pilot underwriting
**Internal operating model • 2026-10-08 • NOT APPROVED PRICING OR A CUSTOMER OFFER**

## Why this is necessary
The existing `freight/deal_economics.py` intentionally evaluates **fixed-fee** diagnostics and pilots. That remains valid for those separately scoped legacy offers and must not be used to claim profitability for the **$0-upfront, recovery-fee-only** founding offer in `freight/FOUNDING_CUSTOMER_PROGRAM.md`. Even a spotless audit can realize **$0**. If a qualified analyst spends 19 hours on that audit, labor is not free just because the founder supplied it.

The rate `DEFAULT_CONTINGENCY_RECOVERY_RATE = Decimal("0.30")` in `freight/commercial_terms.py` is a **software default**, not source evidence of a signed customer-specific contingency rate or entitlement to bill. The value in this document's fixture (20%) is explicitly a **synthetic what-if assumption**, not an approved RETALLY rate or founding discount.

## New versioned code
- `zero_upfront_underwriting.py`: strict schema/Decimal-based illustrative cost and recovery-risk model.
- `fixtures/zero_upfront_synthetic_example.json`: completely synthetic 20-invoice-example assumptions; no actual client data.
- `test_zero_upfront_underwriting.py`: 15 tests for worst-case loss, zero recovery, fee eligibility, evidence flags, overrun caps, cost precision and rejection of real-person input.
- Existing CI `.github/workflows/freight-contracts.yml` runs the tests alongside Mission 2G gates.

## Evidence and equations
Review hours = analyst + independent reviewer + administrative hours.

Fully loaded exposure = hours × cost per hour + direct delivery costs + potential recovery administration costs. Founder labor **must** have a positive hourly cost. This is a cost budget, not a guaranteed cash payment.

**No-recovery outcome**: customer pays no contingency fee; RETALLY's at-risk delivery cost is the full exposure.

**Synthetic expected fee (what-if only)**:
assumed supported opportunity × assumed realized fraction × assumed uniquely attributable fraction × assumed fee-eligibility fraction × hypothetical rate.

**Break-even actual fee-eligible receipts**: delivery exposure ÷ hypothetical rate, only if the rate becomes contractually accepted. Expected-value scenarios do **not** prove that actual recoveries or legal eligibility will exist.

### Synthetic example, not a forecast or quote
| Category | Figure |
|---|---:|
| Hypothetical supported opportunity | $50,000 |
| Assumed realized / attribution / fee-eligibility fractions | 65% / 80% / 90% |
| Hypothetical fee rate | 20%, not RETALLY's approved price |
| Analyst / reviewer / admin hours | 14 / 3 / 2 (19 total) |
| Loaded labor cost | $100/hour |
| Additional delivery + recovery administration | $250 + $350 |
| RETALLY delivery exposure | **$2,500** |
| Customer's recovery fee if actual recovery is zero | **$0** |
| RETALLY downside if actual recovery is zero | **−$2,500** |
| Modeled expected fee, based solely on invented probabilities | $4,680 |
| Modeled expected contribution, not actual profit | $2,180 |
| Fee-eligible cash required merely to break even at illustrative rate | **$12,500** |
| Modeled scope limit | 20 hours and $2,600 loss allowance |
| Actual signed rate / buyer scope / secured intake / reviewer | **NOT APPROVED/VERIFIED** |
| Decision | **HOLD**, not ready to accept work |

There is no financial evidence in this synthetic scenario that RETALLY can recover $50,000, realize the assumed fractions, or achieve the modeled profit. This example may **not** appear in customer materials as a business case.

## Operations for first three actual engagements
1. **No-confidential-data qualification**: non-sensitive metadata, mode/carriers/period, availability of rate documents, prior auditor, candidate dispute; client identity and inbox confirmed. No invoice uploaded or attached.
2. **Bounded sample decision**: specify invoice count, selection method, authorized analyst hours and worst-case monetary limit **before** commencing review. Escalate if evidence missing or cost cap exceeded. Default to **HOLD** for unbounded costs.
3. **Buyer-specific legal & secure intake approval**: only the existing gate in `first_customer_gate.py` plus the real buyer-signed authorization, counsel-approved rates and verified separate-environment evidence can permit real confidential data. This underwriting output can **never** sign or approve the engagement.
4. **No guaranteed recovery thesis**: stop when fixed review budget exhausted; independently record a defensible clean/no-recovery outcome if true. No fee applies when actual contractually eligible receipts are $0.
5. **Later contingency engagement**: new written claims authority, separate fee terms and carrier action approvals. Uncollected potential or carrier approval is not money received. Reversals adjust realized amounts and may affect fees under the actual contract.
6. **Separate customer/private records**: never put live invoice values, firm identities, contact details or pricing negotiations in this public repository or fixture.

## How to run
```sh
PYTHONPATH=. python -m unittest discover -s freight/commercial -p 'test_zero_upfront_underwriting.py' -v
python freight/commercial/zero_upfront_underwriting.py freight/commercial/fixtures/zero_upfront_synthetic_example.json
# The following MUST return exit status 2 on the current unapproved demonstration:
python freight/commercial/zero_upfront_underwriting.py freight/commercial/fixtures/zero_upfront_synthetic_example.json --require-human-review-eligible
```

## Failure modes and owners
- **Inconsistent advertised pricing:** program owner and qualified counsel must confirm the initial free review and any future separately agreed success fee.
- **No actual signed rate:** owner/counsel; avoid treating code default 30% or invented 20% as contractual evidence.
- **No verifiable inbound mail:** company mailbox owner; sender's SENT messages and DNS are insufficient.
- **Buyer-specific data permissions missing:** buyer IT and RETALLY verifier; a baseline empty workspace isn't automatically ready for a customer's freight records.
- **Sample's unexplained $1,650:** finance reviewer; preserve UNVERIFIED in customer samples.
- **No independent reviewer capacity / unlimited founder hours:** operations owner; fail closed rather than assuming free labor.

**Commercial release remains blocked.** Tests are not buyer acceptance, projections are not results, and a pricing illustration is not a signed contract.
