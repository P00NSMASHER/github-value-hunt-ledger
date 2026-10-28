# Golden Goose: bounty-market reality check

Observation date: **October 28, 2026**. This is an independently checked **sample of one Algora organisation's published open listings**, not a statement about the entire coding-bounty market. This research is not a monetization claim and does not change any hunter, production, or protected-branch governance.

## Why this matters

The tscircuit Algora page displayed **10 open bounty entries / $450 advertised**, mapping to **six distinct GitHub issues**. Cross-checking the live GitHub issue pages showed:

* Seven listed rewards totalling **$367** were attached to three CLOSED issues (five separate listings on the same dsn-converter issue).
* One reward totalling **$50** was attached to an OPEN issue in an ARCHIVED read-only repo.
* One reward of **$30** pointed to a GitHub issue URL that returned 404; mark as UNVERIFIED rather than treating it as fake or closed.
* One reward of **$3** pointed to an OPEN issue with 39 reported claims. It cannot satisfy a first-$100 minimum by itself.

Therefore **$417 / $450 = 92.7%** of that board's advertised money was attached to confirmed closed/archived destinations. **No bounty in this ten-listing sample passed the conservative first-$100 screen**; neither a $450 payout nor any measurable income follows from the advertised board. This does not imply that all Algora payouts are suspect; its own public board lists past completed payments.

## Sources

* Advertised board: https://algora.io/tscircuit/bounties?status=open
* Closed: https://github.com/tscircuit/jlcsearch/issues/92
* Closed (five rewards): https://github.com/tscircuit/dsn-converter/issues/54
* Closed: https://github.com/tscircuit/tscircuit/issues/1130
* Archived, read-only: https://github.com/tscircuit/autorouting/issues/92
* Open but low-value/high competition: https://github.com/tscircuit/pcb-viewer/issues/163
* Unresolved/missing issue path: https://github.com/tscircuit/pgstrap/issues/2
* Opire payment rule is **approval followed by payer-arranged payment**, not automatic cashout: https://docs.opire.dev/rewards/pricing

## Deterministic read-only screen

The offline Python standard-library tool consumes explicitly verified JSON records. It never scrapes websites, claims bounties, sends messages, submits code, requests secrets, executes trades or makes a financial promise. When data are missing or contradictory it does **not** assert an eligible payout. Multiple listed awards on one issue are grouped for work triage, rather than misrepresented as separate guaranteed jobs.

```sh
python3 research/golden_goose/bounty_triage.py research/golden_goose/bounty_census_2026-10-28.json
cd research/golden_goose && python3 -m unittest -q test_bounty_triage.py
```

Fifteen local unit tests passed prior to submitting this draft, including the recorded $417/10/6 census regression. That is a **local synthetic test**, not independent production acceptance.

**Conclusion:** Do not pursue the sampled board as a first-$100 target. Continue the broader Golden Goose hunt, but require current GitHub issue status, nonarchived repo, outside-solver eligibility, reward credibility, recent awarded payouts, low competition, realistic implementation hours, and contributor authorization before coding for money. Even a row that passes remains review-ready rather than payable. Track alongside https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863 without promoting it to MASTER or claiming generated hunter leases.

## Independent source check 2: verified open != eligible to earn (2026-10-28)

A direct GitHub issue search on `tenstorrent/tt-metal` returned **three currently open** bounty-labelled issues in the checked result (not an exhaustive market census), totalling **$6,750** in advertised rewards:

| Issue | Advertised | GitHub status | Current assignee | First-$100 eligibility for this account |
| --- | ---: | --- | --- | --- |
| [#62571 Qwen3-TTS predictor](https://github.com/tenstorrent/tt-metal/issues/62571) | $750 | OPEN | `bvdyvncqr5-commits` | BLOCKED, assigned elsewhere |
| [#59732 Sampling distribution bias](https://github.com/tenstorrent/tt-metal/issues/59732) | $3,000 | OPEN | `samiyadev786` | BLOCKED, assigned elsewhere |
| [#56908 Distributed normalization row stride](https://github.com/tenstorrent/tt-metal/issues/56908) | $3,000 | OPEN | `Adraca` | BLOCKED, assigned elsewhere |

**Controlling terms:** [Tenstorrent Contribution Program Terms](https://docs.tenstorrent.com/bounty_terms.html), October 2026, sections 2 and 5: payment requires GitHub assignment **at PR submission time**; submitting to an issue already assigned to another is not eligible. Tenstorrent also reserves award discretion. All three tasks require specialized hardware validation. The figures are **advertised opportunity size only**: *verified earned, payable, or collected by us = $0*.

The new [3-row synthetic-free read-only observation fixture](tenstorrent_open_assigned_2026-10-28.json) is source-bound as of 2026-10-28. The assignment-aware classifier now distinguishes `external_contributors_allowed=true` (eligible people can contribute to the program) from `assigned_to_other=true` (this particular bounty cannot be collected by us). It blocks the latter and fails closed on missing assignment policy, even when issue state is OPEN and value exceeds $100.

**Validation status:** one observed negative-control dataset was committed, and six extra unit tests (one census regression, five adversarial assignment cases) were added. The original 15 tests had passed before this update; the enlarged 21-test suite has **not yet been independently executed or accepted**, so do not claim it passes. No bounty was claimed and no outside contributor contacted.

**Updated decision:** demote coding bounties for near-term revenue unless a candidate has verified unassigned/authorized ownership, an enforceable enough payment route, available verification hardware, and a realistic short implementation. Next cheapest test: find a newly posted, unassigned, non-hardware $100+ task and confirm the controlling payment terms on the issuer's own page *before writing solution code*.
