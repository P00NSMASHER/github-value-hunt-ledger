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
