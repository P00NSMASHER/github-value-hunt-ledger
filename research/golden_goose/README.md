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


## Independent source check 3: cross-board listed rewards versus actual contributor opportunity (2026-10-28)

**Sample design:** four **purposively chosen** advertised Algora/Jobbi rewards in four different GitHub repositories, each >=$100. This is an adversarial negative-control sample, **not random or a bounty-market prevalence estimate**. Cross-checked the repository issue state, labels, assignment and visible competing PRs through first-party GitHub issue and repository readbacks. The **$800** sum is advertised gross, **not** an offer to this contributor, escrow proof, receivable or revenue.

| GitHub issue | Listed | Primary-source counterevidence | Conservative disposition |
| --- | ---: | --- | --- |
| [coolify#2378](https://github.com/coollabsio/coolify/issues/2378) | $100 | Explicit current `👥 Core Team Only` label; public index misleading for outside developers | `BLOCKED_EXTERNAL_RESTRICTION` |
| [revert#372](https://github.com/revertinc/revert/issues/372) | $100 | Open but assigned to `ezhil56x`; no right to assume another solver's payout | `BLOCKED_ASSIGNED_TO_OTHER` |
| [py-workedtask#4](https://github.com/javelin-anticheat/py-workedtask/issues/4) | $100 | Nine-or-more visible historical attempts/claims; substantial competition and no verified fresh award authority | `UNVERIFIED_OR_HIGH_COMPETITION` |
| [gyroflow#742](https://github.com/gyroflow/gyroflow/issues/742) | $500 | Multiple overlapping open PRs (at least #1118, #1214, #1218, #1221); current GitHub labels do not themselves verify active paid award | `UNVERIFIED_OR_HIGH_COMPETITION` |

**Denominators:** four examined / four still OPEN on GitHub / four no independently proven review-ready first-$100 tasks. **$800 advertised, $0 independently collectible or earned.** These observations cannot establish that the four bounties will never pay an eligible solver; they show no present authority for *our* action. Jobbi's broader Oct. 28 index advertises **742 open gigs, $49,183 total priced value and $20 median reward**, but its index is not a payment ledger and spans different boards. [Jobbi market report](https://jobbi.org/gigs/report); [Jobbi Algora listings](https://jobbi.org/gigs/boards/algora). [BountyOS](https://bountyos.rovidev.com/en/github-bounty-board/) already markets stricter verification (with paid access to issue identities), so a generic paid bounty curator is **not an unoccupied market**; no independent customer/payment evidence for such a competing service was established.

**New reusable artifacts:** `bounty_cross_board_2026-10-28.json` records the four issue URLs, listing sources, observed labels/assignees, explicit confidence limitations and competing-PR references. `test_bounty_cross_board.py` contains four adversarial regression tests, and the existing classifier distinguishes **explicit prohibition** from **unknown eligibility**, and treats observed assignment or high competition as a negative even if other fields are unknown. The existing unit-test file gained four new boundary tests. This research branch and test files have been written/read back from GitHub; **tests have not been executed or independently accepted in this iteration**. Run from `research/golden_goose/`:

```sh
python3 -m unittest -q test_bounty_triage.py test_bounty_cross_board.py
python3 bounty_triage.py bounty_cross_board_2026-10-28.json
```

**Decision:** **deprioritize generic GitHub bounty-hunting as a near-term first-$100 strategy**. Sampled sources are stale/restricted/assigned/contested and require unapproved contributor claims, external submissions and eventual discretionary award. Do not extrapolate a market-wide failure rate from a targeted negative sample. Maintain the fail-closed screen as a reusable component only. The next research iteration should pursue a materially different first-dollar source (e.g. validated customer-backed service demand) rather than adding more static bounty-listing aggregators. Preserve PR as DRAFT, all protected-branch controls and the portfolio's existing ranked priorities.
