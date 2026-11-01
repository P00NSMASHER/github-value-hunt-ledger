# RETALLY | Approved Brand Foundation

Status: **brand design and messaging direction approved; production rebrand NOT yet deployed.** This file records the user-approved identity and messaging for future implementation. It does not authorize a trade-name representation before clearance or change any contracts.

## Identity

- Company brand / proposed trading name: **RETALLY**
- Primary logo: **RETALLY wordmark** in glossy charcoal with **only the letter A** in glossy emerald. The wordmark stands alone in headers/navigation; do not automatically append the oversized R symbol to it.
- Secondary brand mark: **standalone oversized R emblem**, green-and-charcoal glossy ribbon construction. Use for favicon, app icon, report cover, and small identity applications.
- Both marks MUST be reproduced from the actual user-approved artwork, not regenerated, redrawn or substituted with a font. The wordmark and emblem have been intentionally split.
- Source-approved wordmark PNG SHA-256: `3c9392cfbb29a2aec88803550071a64b5d86f61b71e430f1da007c8d368b1ae1`
- Source-approved emblem PNG SHA-256: `3bce87a3d79e78ccb08d9baf408da8ac4a0c0acaaba1435f4e1078854557c986`
- The original binary logo masters are in the user-reviewed RETALLY brand starter ZIP, **not yet stored in this repository**. Upload exact checked bytes in a separate production asset PR; do not approximate from examples.

## Approved core messaging

**Tagline: Find it. Prove it. Recover it.**

**Positioning: We find freight billing errors, document the evidence, and help recover overpayments.**

Brand voice: **direct, assured, precise, and commercially focused.** Plain language; active verbs; short sentences. Do not return to the earlier tagline as the core line. Do not invent refunds, recovery rates, clients, certifications, or service guarantees.

**Three-step buyer explanation:**
1. **Find it.** Review freight invoices, shipment records, and applicable rates for possible billing errors.
2. **Prove it.** Document the charge, controlling terms, and the evidence supporting each reviewed discrepancy.
3. **Recover it.** With customer approval, help pursue eligible overpayments and track the actual outcome.

**CTA:** Request a free audit. Scope, eligibility, fee terms, and recovery actions must remain aligned with the existing freight engagement controls; recovery is not guaranteed.

## Visual foundation

- Midnight Ink: `#0E1E29`
- Deep Forest: `#06392F`
- Pine: `#062C26`
- Emerald accent: `#05B873`
- Fresh Jade: `#20DDA1`
- Mist: `#EFF5F2`
- White: `#FFFFFF`
- Ledger Gray: `#576D71`
- Use modern legible sans-serif; use the original artwork for the wordmark (not typed letters). The color values are **digital UI design tokens**, not print-industry ink specifications.
- Office printing: grayscale derivatives are only proofs, not production-ready 1-color vector files. Require an accurate manual vector master and proof it.

## Commercial and evidence standard

Keep the production controls in `freight/FREIGHT_RECOVERY_EVIDENCE_STANDARD.md`, the engagement model, authorized claims and customer data handling unchanged. Differentiate a *potential error*, *supported finding*, *customer-authorized claim*, and *actual received or posted recovery*. Do not treat a proposed saving as recovered funds.

The actual customer-facing source today is `freight/site/` in this repository. **No live site, outreach, forms, portal, pricing, contracts, email identity, domain, or metadata is changed by this document.**

## Migration gates (do not bypass)

1. Independently clear RETALLY's business name and mark across relevant classes/common-law users; confirm correct trading entity and state obligations. Check domain and handles; availability is unverified.
2. Upload and QA the approved source image bytes. Produce print, light/dark, favicon and OG derivatives without altering the marks.
3. Propose a separate visual migration PR for `freight/site/`: nav/logo, titles, metadata, JSON-LD, social cards, privacy/trust references, reports and redirect strategy. Keep previously working URL and intake pathways.
4. Ensure accurate verified sender identity, postal address and legally sufficient opt-out language in commercial outreach. No automatic mail or announcement.
5. Run accessible mobile/tablet/desktop screenshot QA, monochrome print proof, internal synthetic form/journey testing and exact-head CI. Do not claim security certification from a marketing design.
6. Release only after legal/operational approval and a separate verified production deploy.

## Created concept deliverables

User-reviewed download package created outside the repository: *RETALLY Brand Starter v1* containing the preserved logo artwork, eight-page PDF brand guide, buyer one-pager, self-contained desktop/mobile website preview, editable HTML/CSS, signature template and supporting design files. The local ZIP is a handoff artifact, not a live customer-facing website. A production implementation must ingest the approved assets before attempting a final identity rollout.
