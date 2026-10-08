# RETALLY Three-Touch Outbound Sequence

Version: 1.2
Effective: 2026-10-07

**Send gate:** Email drafts contain a required postal-address placeholder, not a deliverable address. Do not send without a verified authorized business mailing address and applicable legal/opt-out checks.

## Rules

- Run the private pre-send gate in OUTREACH_SAFETY.md immediately before every touch. A draft is not a send; reconcile Gmail Sent and replies first.
- Use one private account ID across recipient aliases. Reserve each recipient/account atomically before sending; unresolved transport results block retry.
- Include the complete sender identity, postal address, and explicit opt-out in every new plain-text and HTML body, including follow-ups. Quoted history is insufficient.
- Three touches maximum unless the prospect substantively engages.
- Day 1, Day 5, Day 12.
- Stop immediately on opt-out, negative response, hard bounce, or clear no-fit.
- Do not send attachments on Touch 1.
- Do not request invoices, contracts, credentials, payment data, or unrestricted access by email.
- Use a verified business address/contact route only.
- One evidence-backed personalization fact is required for top-25 accounts.
- Choose FIRST-LOOK or SECOND-LOOK before drafting.

## Touch 1 — evidence-first introduction

Subject options:
- Freight billing review for {{company}}
- Independent second look at freight billing for {{company}}
- Question for whoever owns freight/AP at {{company}}

FIRST-LOOK body:

Hi {{first_name_or_company_team}},

{{personalization_sentence}}

I run RETALLY. We review past freight invoices for duplicate charges, rate differences, unsupported accessorials, and missed credits. The initial audit has no upfront fee.

Each reviewed finding includes the invoice, shipment records, and applicable rate terms. If you choose to authorize recovery work, our fee applies only to eligible funds actually recovered.

Would you be the right person for freight/AP review, or could you point me to whoever owns it?

Thanks,
Jamison
RETALLY
[VERIFIED BUSINESS MAILING ADDRESS REQUIRED BEFORE SEND]

Reply "no thanks" and I won't follow up.

SECOND-LOOK body:

Hi {{first_name_or_company_team}},

{{personalization_sentence}}

Does {{company}} already review freight invoices through a TMS, payment provider, or internal team?

RETALLY offers an independent second look at an agreed set of historical invoices, with no upfront audit fee. We account for existing findings, automatic credits, and claims already known to your provider before identifying any additional opportunity.

Would you be the right person for that review, or could you point me to whoever owns freight/AP?

Thanks,
Jamison
RETALLY
[VERIFIED BUSINESS MAILING ADDRESS REQUIRED BEFORE SEND]

Reply "no thanks" and I won't follow up.

## Touch 2 — Day 5 — give something useful

Subject: Re: {{original_subject}}

Hi {{first_name_or_company_team}},

Here is a short guide to the evidence behind a freight billing review:

{{methodology_url}}

The short version: candidate differences, validated findings, approved claims, and actual recovered funds stay separate, and existing/automatic credits are not counted as ours.

Would an independent review of past freight invoices be useful for {{company}}? If another team owns this, I would appreciate a pointer.

Thanks,
Jamison
RETALLY
[VERIFIED BUSINESS MAILING ADDRESS REQUIRED BEFORE SEND]

Reply "no thanks" and I won't follow up.

## Touch 3 — Day 12 — close the loop

Subject: Re: {{original_subject}}

Hi {{first_name_or_company_team}},

I'm closing the loop so I don't keep filling your inbox.

If freight invoice review sits with someone else at {{company}}, I'd appreciate the direction. Otherwise I'll close this out and won't continue following up.

Thanks,
Jamison
RETALLY
[VERIFIED BUSINESS MAILING ADDRESS REQUIRED BEFORE SEND]

Reply "no thanks" and I won't follow up.

## Reply handling

Positive / interested:
- stop sequence;
- qualify freight volume, modes, history, current controls, records, buyer, and secure-intake readiness;
- route to founding program when qualified and capacity remains.

Referral:
- thank sender;
- create a fresh account/contact record for the referred person;
- preserve the referral context;
- do not continue the old sequence against the referrer.

Already audits freight:
- switch to Second-Look offer;
- explicitly state existing findings/credits remain theirs.

Not interested / opt-out:
- acknowledge once if appropriate;
- suppress permanently from campaign follow-up.

Bounce:
- do not retry guessed variants;
- research another official route.

No reply after Touch 3:
- close as CLOSED_NO_REPLY;
- no further sequence until a new material trigger exists.

## Metrics

Track:
- delivered;
- hard bounce;
- positive reply;
- referral;
- negative reply;
- opt-out;
- qualified conversation;
- secure-intake-ready;
- audit authorized;
- founding-program accepted;
- first-look vs second-look;
- time to reply;
- time to authorized audit.
