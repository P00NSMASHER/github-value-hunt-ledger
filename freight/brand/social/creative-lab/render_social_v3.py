#!/usr/bin/env python3
"""Six additional RETALLY visual concepts, offline and strictly draft-only.

Shares the proven v2 screenshot/brand-security runner and uses independently
art-directed layouts. Every input illustration is labelled non-customer data.
This module NEVER posts, uploads, schedules, claims recovered cash or marks
rendered assets as approved.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import render_social as base

CONCEPTS = (
    "scope_first", "fuel_authority", "detention_clock",
    "claim_evidence", "settlement_status", "secure_intake",
)

# A distinct, pre-existing registered website master per editorial topic.
# Public website inclusion does NOT prove social publication rights.
CANONICAL_HERO_PHOTOS = {
    "scope_first": "freight-network.webp",
    "fuel_authority": "rate-authority.webp",
    "detention_clock": "warehouse-handoff.webp",
    "claim_evidence": "invoice-evidence.webp",
    "settlement_status": "approved-path.webp",
    "secure_intake": "dock-control.webp",
}

# Static, carefully qualified editorial content. No fabricated rates, events,
# clients, refunds, carrier logos, or credentials.
COPY = {
    "scope_first": {
        "style": "scope", "issue": "04 / 09", "subissue": "SCOPE CONTROL",
        "kicker": "A bounded freight-audit population",
        "title": "SCOPE FIRST.<br><span class='accent'>THEN AUDIT.</span>",
        "subtitle": "Before flagging a charge,<br>decide which invoices belong.",
        "pill": "NO CHANGING THE DENOMINATOR MID-REVIEW",
        "eyebrow": "THE SCOPE FREEZE",
        "section": "Define what you're actually testing.",
        "cards": [
            ("01 / ENTITY", "DEFINE", "CARRIERS", "INCLUDE OR EXCLUDE", "List carriers"),
            ("02 / PERIOD", "FREEZE", "DATE RANGE", "COVERAGE", "Set the window"),
            ("03 / HISTORY", "RECONCILE", "PRIOR CREDITS", "DON'T COUNT TWICE", "Deduplicate"),
        ],
        "focus": 1,
        "note": "Freeze carrier, dates, mode and existing credits first.",
        "action": "SAVE THE SCOPE →",
        "caption_hook": "A freight audit starts with a denominator—not a dollar sign.",
        "site_slug": "freight-invoice-audit-checklist",
        "alt": "RETALLY illustration of a bounded freight-audit population with carriers, invoice date coverage and already-issued credits. No real customer data or results.",
    },
    "fuel_authority": {
        "style": "fuel", "issue": "05 / 09", "subissue": "FUEL SURCHARGE",
        "kicker": "Carrier-rate evidence",
        "title": "FUEL FEES.<br><span class='accent'>WHICH RULE?</span>",
        "subtitle": "Verify the controlling index period<br>and contract schedule.",
        "pill": "THE PUBLISHED INDEX IS NOT THE CONTRACT",
        "eyebrow": "THE RATE AUTHORITY",
        "section": "Rebuild the calculation with evidence.",
        "cards": [
            ("01 / TERMS", "SOURCE", "AGREEMENT", "WHAT GOVERNS?", "Check contract"),
            ("02 / PERIOD", "EFFECTIVE", "FUEL INDEX", "WHICH WINDOW?", "Verify dates"),
            ("03 / CHARGE", "CALCULATION", "RATE BASE", "ROUNDING RULE", "Recalculate"),
        ],
        "focus": 1,
        "note": "A lower downloaded table does not prove an error.",
        "action": "CHECK THE RULE →",
        "caption_hook": "The fuel-surcharge math can be right with the wrong rule.",
        "site_slug": "carrier-rate-audit",
        "alt": "RETALLY editorial fuel-surcharge audit diagram showing the rate agreement, fuel index period and invoice charge basis. Hypothetical framework only.",
    },
    "detention_clock": {
        "style": "detention", "issue": "06 / 09", "subissue": "ACCESSORIALS",
        "kicker": "A hypothetical detention review",
        "title": "DETENTION.<br><span class='accent'>CHECK THE CLOCK.</span>",
        "subtitle": "Timestamps raise questions.<br>The governing terms decide.",
        "pill": "ILLUSTRATIVE MATH — NOT A CUSTOMER RESULT",
        "eyebrow": "ILLUSTRATIVE EXAMPLE",
        "section": "150 minutes onsite. What is billable?",
        "cards": [
            ("GATE-IN", "SAMPLE", "08:30", "START", "Verify trigger"),
            ("GATE-OUT", "SAMPLE", "11:00", "END", "Check record"),
            ("FREE TIME", "ASSUMED", "120 MIN", "TERMS", "30 min beyond"),
        ],
        "focus": 2,
        "note": "Billed detention still needs contract, triggers and credits.",
        "action": "VERIFY THE TERMS →",
        "caption_hook": "90 minutes billed. 30 beyond free time. Is that an overcharge?",
        "site_slug": "accessorial-charge-audit",
        "alt": "Clearly labelled illustrative detention review showing gate-in 08:30, gate-out 11:00 and hypothetical 120-minute free period. Not a customer invoice or a proven overcharge.",
    },
    "claim_evidence": {
        "style": "evidence", "issue": "07 / 09", "subissue": "EVIDENCE PACKAGE",
        "kicker": "Proof-led freight recovery",
        "title": "A FLAG<br><span class='accent'>IS NOT PROOF.</span>",
        "subtitle": "A dispute needs the record<br>that supports the calculation.",
        "pill": "CLAIMS NEED A REPRODUCIBLE PAPER TRAIL",
        "eyebrow": "THE EVIDENCE STANDARD",
        "section": "Make the finding independently reviewable.",
        "cards": [
            ("01 / SHIPMENT", "IDENTITY", "BILL + BOL", "SAME OBLIGATION?", "Match the load"),
            ("02 / TERMS", "AUTHORITY", "RATE SOURCE", "EFFECTIVE DATE", "Verify source"),
            ("03 / AMOUNT", "RECOMPUTE", "CALCULATION", "ALREADY CREDITED?", "Reconcile"),
        ],
        "focus": 2,
        "note": "A supported claim is still not an approved refund.",
        "action": "SAVE THIS TEST →",
        "caption_hook": "Could somebody else verify the overcharge without calling you?",
        "site_slug": "freight-overcharge-dispute-process",
        "alt": "RETALLY three-part evidence checklist showing shipment identity, governing rate terms and a reproducible charge calculation; no real client records.",
    },
    "settlement_status": {
        "style": "settlement", "issue": "08 / 09", "subissue": "RECOVERY STATUS",
        "kicker": "Realized recovery versus estimates",
        "title": "APPROVED<br><span class='accent'>ISN'T PAID.</span>",
        "subtitle": "Trace the claim, usable credit<br>and any later reversal.",
        "pill": "COUNT ELIGIBLE VALUE ACTUALLY REALIZED",
        "eyebrow": "THE RECOVERY LEDGER",
        "section": "Three statuses. Three different facts.",
        "cards": [
            ("01 / CLAIM", "DECISION", "APPROVED", "NOT CASH YET", "Validate decision"),
            ("02 / CREDIT", "FINANCIAL", "POSTED", "USABLE AMOUNT", "Verify receipt"),
            ("03 / REVERSAL", "NET", "ADJUSTED", "RECONCILE", "Calculate net"),
        ],
        "focus": 1,
        "note": "A posted credit can be reversed. Report net realized value.",
        "action": "TRACE THE CREDIT →",
        "caption_hook": "A carrier approved the credit. Has money really been recovered?",
        "site_slug": "freight-recovery-evidence-standard",
        "alt": "RETALLY illustrative recovery ledger distinguishing an approved claim, posted usable credit and potential reversal, without fabricated dollar amounts or customer results.",
    },
    "secure_intake": {
        "style": "security", "issue": "09 / 09", "subissue": "DATA STEWARDSHIP",
        "kicker": "Confidential freight records",
        "title": "NO INVOICES<br><span class='accent'>IN DMS.</span>",
        "subtitle": "Discuss the review scope first.<br>Transfer records only by approved means.",
        "pill": "PUBLIC MESSAGES ARE NOT SECURE FILE INTAKE",
        "eyebrow": "THE PRIVACY BOUNDARY",
        "section": "Separate the conversation from the records.",
        "cards": [
            ("01 / INITIAL", "GENERAL", "SCOPE", "MODES + PERIOD", "No private files"),
            ("02 / APPROVAL", "SEPARATE", "SECURE ROUTE", "AGREE TRANSFER", "Confirm method"),
            ("03 / MATERIAL", "RESTRICTED", "INVOICES", "NEVER VIA DM", "Keep records private"),
        ],
        "focus": 1,
        "note": "Never send private rates, invoices or bank details by DM.",
        "action": "SHARE THE RULE →",
        "caption_hook": "Your confidential freight invoices do not belong in social DMs.",
        "site_slug": "privacy",
        "alt": "RETALLY privacy graphic contrasting general freight-scope questions with separately agreed secure record transfer, warning against sending invoices through public social messages.",
    },
}

# Distinct visual subfamilies share approved physical brand geometry, but the
# information visuals, focus, typography and mood differ per topic.
CSS_V3 = r"""
.v3 .hero:after{opacity:.15}
.v3 .hero-title{font-size:87px;letter-spacing:-4.7px;line-height:1.05;margin:23px 0 22px;max-width:950px}
.v3 .hero-body{top:230px}
.v3 .hero-sub{font-size:29px;line-height:1.31}
.v3 .upper-pill{font-size:17px;margin-top:20px;max-width:935px;white-space:normal}
.v3 .paper{top:697px}
.v3 .section-title{font-size:34px;letter-spacing:-.9px}
.v3 .documents{top:218px;height:282px;gap:16px}
.v3 .document{padding:25px 19px;border-radius:22px}
.v3 .doc-top{font-size:17px;letter-spacing:.3px;gap:4px}
.v3 .doc-type{font-size:33px;line-height:1.03;margin:24px 0 12px;letter-spacing:-.7px}
.v3 .doc-label{font-size:16px;letter-spacing:.6px;margin:16px 0 8px}
.v3 .doc-value{font-size:24px;padding:11px;line-height:1.23}
.v3 .document.focus{transform:translateY(-8px) rotateX(1.6deg)}
.v3 .keypoint{top:521px}
.v3 .keypoint strong{font-size:23px;line-height:1.17}
.v3 .keypoint em{font-size:16px}
.v3 .connector{display:none}
.v3 .footer-note{font-size:17px}
.scope .hero{background:#061f20}
.scope .photo{background-image:linear-gradient(92deg,rgba(4,26,29,.94),rgba(6,29,28,.76) 58%,rgba(6,25,26,.08)),url('__PHOTO__');background-position:60% 57%}
.scope .paper{background:linear-gradient(150deg,#f6fbf7,#eaf6ed)}
.scope .document:nth-child(1){background:linear-gradient(145deg,#fff,#eef6ef)}
.scope .document:nth-child(3){background:linear-gradient(145deg,#fff,#e3f0eb)}
.fuel .photo{background-position:43% 48%;filter:saturate(.81) contrast(1.2)}
.fuel .paper{background:linear-gradient(145deg,#093c36,#051e1e);box-shadow:0 -28px 78px #001e2080}
.fuel .paper .section-title,.fuel .paper .keypoint strong{color:#ebfff3}
.fuel .paper .eyebrow,.fuel .paper .keypoint em{color:#8ff3c1}
.fuel .paper .sample,.fuel .paper .footer-note{color:#bbdacb}
.fuel .paper .sample b{color:#9aefcb}
.fuel .paper .divider{background:linear-gradient(90deg,#34e3a3,#59887f22)}
.fuel .paper .keypoint{border-top-color:#649f8a50}
.fuel .document{border-color:#7bcbb382;box-shadow:0 6px 0 #407966,0 22px 40px #0006}
.fuel .document.focus{background:linear-gradient(136deg,#eafff4,#ddffed)}
.detention .photo{background-position:70% 60%;filter:saturate(.91) contrast(1.1)}
.detention .hero-title{font-size:77px;letter-spacing:-4.1px}
.detention .paper{background:linear-gradient(153deg,#fffdfa,#e6f1ef)}
.detention .document .doc-type{font-size:53px;letter-spacing:-2px;color:#025d47;margin:28px 0 20px}
.detention .document.focus .doc-type{color:#03281e}
.detention .document .doc-top{font-size:17px}
.detention .document .doc-value{font-size:19px}
.detention .keypoint strong{max-width:720px}
.evidence .photo{background-position:60% 51%;filter:saturate(.75) contrast(1.27)}
.evidence .hero-title{font-size:95px}
.evidence .paper{background:linear-gradient(160deg,#eff9f4,#fbfff9)}
.evidence .document:nth-child(1){transform:rotate(-1.8deg)}
.evidence .document:nth-child(2){transform:translateY(-8px) rotateX(1.7deg);background:linear-gradient(145deg,#ecfff5,#e1f8eb)}
.settlement .photo{background-position:65% 56%;filter:saturate(1.35) contrast(1.12)}
.settlement .paper{background:linear-gradient(159deg,#f3fff7,#e7f5f0)}
.settlement .document:nth-child(1){background:#f9fcf6}
.settlement .document:nth-child(2){background:linear-gradient(145deg,#deffee,#f5fff9)}
.settlement .document:nth-child(3){border-color:#e6d2ba;background:linear-gradient(145deg,#fff,#fff5ed)}
.settlement .document:nth-child(3) .doc-type{color:#865f20}
.settlement .document:nth-child(2) .doc-type{color:#007b51}
.security .photo{background-image:linear-gradient(99deg,rgba(3,21,35,.95),rgba(8,32,43,.7) 48%,rgba(12,43,54,.15)),url('__PHOTO__');background-position:38% 58%;filter:saturate(.8)}
.security .paper{background:linear-gradient(150deg,#e9f1fa,#f9fdf9)}
.security .section-title{color:#153d49}
.security .document{border-color:#d6e5ec;background:linear-gradient(140deg,#fff,#f0f7f7)}
.security .document.focus{border-color:#24a779;background:linear-gradient(142deg,#dcffea,#f4fff9)}
.security .document:nth-child(3){border-color:#ecd8d0;background:linear-gradient(142deg,#fff,#fff4ed)}
.security .document:nth-child(3) .doc-type{color:#995139}
.security .eyebrow{color:#19715c}
.security .keypoint strong{color:#24434a}
"""


def template_html(logo: str, photo: str, concept: str, preview: bool = False) -> str:
    if concept not in CONCEPTS:
        raise ValueError(f"Unknown new topic: {concept}")
    c = COPY[concept]
    top = base._common_top(
        html.escape(c["kicker"]), html.escape(c["issue"]), html.escape(c["subissue"]),
        c["title"], c["subtitle"], html.escape(c["pill"]))
    paper = base._paper_start(html.escape(c["eyebrow"]), html.escape(c["section"]))
    for idx, spec in enumerate(c["cards"]):
        prefix, state, title, label, value = spec
        paper += base._card(*(html.escape(v) for v in (prefix,state,title,label,value)),
                            highlight=(idx == c["focus"]))
    paper += base._paper_end(html.escape(c["note"]), html.escape(c["action"]))
    content = base.CSS + "\n" + CSS_V3
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY — draft-only freight-finance field notes</title>'
        '<style>' + content + '</style></head><body><main class="artboard v3 ' +
        c["style"] + '">' + top + paper
    )
    if preview:
        document += '<div class="preview">DESIGN CONCEPT ONLY · NOT APPROVED FOR PUBLICATION</div>'
    document += '</main></body></html>'
    document = document.replace("__LOGO__",logo).replace("__PHOTO__",photo)
    if "http://" in document or "https://" in document or any(x in document.lower() for x in (
            "<script","<iframe","<form")):
        raise ValueError("Unexpected remote/active content in offline graphic")
    return document


def render(output: Path, mode: str, logo: Path, photo: Path,
           *, concept: str = "all", executable: str | None = None) -> dict:
    if mode not in ("production","preview"):
        raise ValueError("Unsupported render mode")
    if concept not in (*CONCEPTS,"all"):
        raise ValueError("Unsupported field notes concept")
    names = list(CONCEPTS) if concept == "all" else [concept]
    # Fail BEFORE the first screenshot or exported folder for a fake logo.
    base.validate_logo(logo)
    if mode == "production":
        if photo.name != "terminal-blue-hour.webp" or photo.parent.name != "images":
            raise ValueError("Production must use canonical website image source directory")
        sources = {name: photo.parent / CANONICAL_HERO_PHOTOS[name] for name in names}
    else:
        sources = {name: photo for name in names}
    for name, path in sources.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or unsafe source photo for {name}")
        base.read_image(path)

    # Reuse the proven screenshot renderer: 1080x1350 plus real 390px feed
    # screenshot, screenshot SHA, DOM clipping checks and network-request veto.
    # Render one topic at a time to supply different locally registered art.
    original_concepts, original_template = base.CONCEPTS, base.template_html
    parts = []
    provenance = {}
    try:
        base.CONCEPTS = CONCEPTS
        base.template_html = template_html
        for name in names:
            sample = base.run(output, mode, name, logo, sources[name],
                              executable=executable)
            parts.extend(sample["assets"])
            provenance[name] = {
                "registered_source_name": sources[name].name,
                "source_sha256": base.sha256(sources[name]),
                "reviewed_for_social_reuse": False,
            }
    finally:
        base.CONCEPTS,base.template_html=original_concepts,original_template
    manifest = {
        "brand":"RETALLY",
        "creative_series":"RETALLY Field Notes v3, draft-only",
        "purpose":"offline sample-only editorial visual review",
        "mode":mode,
        "no_publication":True,
        "network_calls":False,
        "human_approval_required":True,
        "needs_owner_source_rights_and_content_review":True,
        "generated_content_cannot_claim_client_results":True,
        "approved_wordmark_sha256":base.sha256(logo),
        "production_photo_rights_review_required":True,
        "hero_image_provenance":provenance,
        "assets":parts,
        "content_proposals":[],
    }
    for item in parts:
        c = COPY[item["concept"]]
        manifest["content_proposals"].append({
            "concept":item["concept"],
            "caption_hook":c["caption_hook"],
            "recommended_educational_route":"/"+c["site_slug"],
            "proposed_accessibility_alt":c["alt"],
            "image_sha256":item["image_sha256"],
            "approved_for_publication":False,
        })
    Path(output,"manifest.json").write_text(
        json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preview","production"),default="production")
    p.add_argument("--concept",choices=(*CONCEPTS,"all"),default="all")
    p.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[4])
    p.add_argument("--photo",type=Path,default=None,help="Only allowed in preview mode")
    p.add_argument("--logo",type=Path,default=None,help="Preview-only exact approved logo copy")
    p.add_argument("--chromium",default=None)
    p.add_argument("--output-dir",type=Path,default=Path("/tmp/retally-v3-review"))
    args=p.parse_args()
    if args.mode=="production" and (args.photo or args.logo):
        p.error("Production mode forbids asset overrides")
    if args.mode=="preview" and not args.photo:
        p.error("Preview requires a supplied research photo")
    logo=args.logo if args.logo else args.repo_root / base.CANONICAL_WORDMARK
    photo=args.photo if args.photo else args.repo_root / base.CANONICAL_PHOTOS["rate_versions"]
    print(json.dumps(render(args.output_dir,args.mode,logo,photo,
                            concept=args.concept,executable=args.chromium),indent=2))


if __name__=="__main__":
    main()
