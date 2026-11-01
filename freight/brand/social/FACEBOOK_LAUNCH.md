# RETALLY — Facebook Page brand-asset and CTA acceptance

**Page:** https://www.facebook.com/p/Retally-61595467040747/

## Source-of-truth assets

- Existing approved avatar: `retally-facebook-avatar-1024.png`, produced from the verified emblem without altering the mark.
- Cover generator: `build_facebook_cover.py` uses ONLY the original exact `freight/site/assets/brand/retally-wordmark-approved.png` master (1619×257, SHA-256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`). It refuses mismatching masters, including the retired corrupted WebP.
- 1640×624 PNG cover keeps essential wording in a central mobile-safe white card with charcoal/emerald surroundings. Preserve the actual letterforms and the emerald arrow-shaped A in the verified wordmark. No generative replacement.
- Run `python -m pip install 'Pillow==12.3.0'` and `python freight/brand/social/build_facebook_cover.py` from the repository. Or obtain the PNG and avatar from the `RETALLY Facebook brand assets` GitHub Actions artifact; the workflow never publishes to Facebook or the website.

## Acceptance steps in authenticated Page owner session

1. **Profile picture:** Replace blue placeholder R with `retally-facebook-avatar-1024.png`. Preview circular crop, especially mobile size. Confirm the published public profile shows the emerald-and-black folded-R emblem.
2. **Cover:** Upload `retally-facebook-cover-1640x624.png`; check desktop and mobile legibility, logo edges, color, and whether Page UI obscures any essential content. If crop fails, revise generator and rerun. Never upload a mockup or unverified logo.
3. **Button:** Set `Learn More` / `Visit Website` to `https://www.retallyrecovery.com/#start-audit`. No fake booking CTA.
4. **About/website:** Use `https://www.retallyrecovery.com/` (not the old HTTP redirect); display contact email `jay@retallyrecovery.com` if a public email field exists. Positioning: `We find freight billing errors, document the evidence, and help recover overpayments.`
5. **Do not add** a physical address, phone, WhatsApp number, pricing claims, customer case studies, testimonials or paid advertising unless independently verified/authorized. The Page checklist is a suggestion, not a requirement.
6. **Verification:** Check the actual public Page and Facebook link preview, not just the private Page editor. Record completion and exact timestamps in issue #344 only after successful readback.

**Current status at preparation:** Screenshot of Professional Dashboard shows Facebook progress options for adding profile and cover photos and an action button. Screenshot alone does not verify the live public state. A browser automation attempt returned no verified changes. All three publication checks remain open pending authenticated Page owner action. Existing organic post schedules and email-only inquiry safeguards remain unchanged.
