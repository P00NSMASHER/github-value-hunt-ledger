# Freight Recovery Three-Touch Outbound Sequence

Version: 1.1
Effective: 2026-10-07

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

I run Freight Recovery. We perform $0-upfront historical freight audits for supportable duplicate charges, rate discrepancies, unsupported accessorials, missed credits, and related billing issues.

Every validated finding is tied back to its invoice/shipment evidence and controlling commercial authority. If you authorize recovery work, our fee is based only on eligible funds actually recovered.

Would you be the right person for freight/AP review, or could you point me to whoever owns it?

Thanks,
Jamison
Freight Recovery
715 Yorktowne Road
Pottsville, PA 17901

Reply "no thanks" and I won't follow up.

SECOND-LOOK body:

Hi {{first_name_or_company_team}},

{{personalization_sentence}}

If {{company}} already audits freight through a TMS, payment provider, or internal process, that is actually the use case I wanted to ask about.

Freight Recovery runs a $0-upfront independent second look against a frozen historical population. Existing findings, automatic credits, and incumbent-known claims are excluded before we measure any net-new opportunity.

Would you be the right person for that review, or could you point me to whoever owns freight/AP?

Thanks,
Jamison
Freight Recovery
715 Yorktowne Road
Pottsville, PA 17901

Reply "no thanks" and I won't follow up.

## Touch 2 — Day 5 — give something useful

Subject: Re: {{original_subject}}

Hi {{first_name_or_company_team}},

Rather than send a generic "checking in" note, here's the standard we use to keep audit numbers honest:

{{methodology_url}}

The short version: candidate differences, validated findings, approved claims, and actual recovered funds stay separate, and existing/automatic credits are not counted as ours.

If a bounded historical review would be useful for {{company}}, I can start with a $0-upfront audit. If this belongs with someone else, a pointer is enough.

Thanks,
Jamison
Freight Recovery
715 Yorktowne Road
Pottsville, PA 17901

Reply "no thanks" and I won't follow up.

## Touch 3 — Day 12 — close the loop

Subject: Re: {{original_subject}}

Hi {{first_name_or_company_team}},

I'm closing the loop so I don't keep filling your inbox.

If freight invoice review sits with someone else at {{company}}, I'd appreciate the direction. Otherwise I'll close this out and won't continue following up.

Thanks,
Jamison
Freight Recovery
715 Yorktowne Road
Pottsville, PA 17901

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
