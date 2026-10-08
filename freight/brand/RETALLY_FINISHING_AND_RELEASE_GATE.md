# RETALLY brand finishing and release gates

Status: implementation draft. Do not treat these changes as a public launch.

## Original identity
Preserve the approved glossy RETALLY wordmark, green A and separate R. Preserve exact positioning, tagline, and existing Hanken/Instrument typography. The primary logo must not be combined with a large emblem.

## Asset finishing
Use approved source images as read-only inputs. Do not mistake near-white textured source art for native transparency. Review matte cleanup on white, soft mist, deep forest and midnight ink. Test favicon sizes 16/32/48/64. Grayscale and one-color images are separately approved derivatives, not proof of vector fidelity. Do not replace website assets until visually approved.

## Website
Adjust large green surfaces toward midnight ink, white and soft mist. Keep emerald for meaningful actions. Preserve hero photography, site sections, CTA geometry, mobile CTA suppression, calculator math, and contact-flow behavior.

## Customer materials
Use consistent headings, margins, source-backed claims and clear status labels in buyer one-pager, scope proposal, sample audit report, letterhead, referral copy and email signature. Fictional figures are never customer results. Do not include unverified names, contacts, storefront information or financial promises.

## Contact cutover
Cloudflare now shows Zoho MX, SPF, DMARC monitoring and `zmail._domainkey.retallyrecovery.com` DKIM TXT, plus ownership-verification TXT. User reports completing the DKIM setup. **DNS configured is not mailbox verified**: live inbound/outbound delivery and message-header SPF/DKIM/DMARC outcomes remain untested; independent business-name clearance and preview deployment are still required. Keep existing customer routes until the CONTACT_CUTOVER_CHECKLIST passes.

## Release acceptance
Run GitHub CI against this branch's exact head. Check mobile 320, 353, 375, 390, 428 and desktop 1280/1440 widths. Render document pages and inspect footers. Confirm HTTPS, SEO canonical, real send/receive, mail auth, and lead receipt before new-domain launch. Name and contracting entity clearance are separate gates. No DNS, mailbox or customer messages should change solely because this draft is merged.