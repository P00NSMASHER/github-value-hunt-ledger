# Portfolio Planning Bridge Contract

## Purpose

The production portfolio planner converts verified read-only state from `ai_business_os_prod`
into a deterministic proposed work queue for the AI Business OS agent fleet and the Hunter system.

It answers one question only:

> Given the evidence gaps that exist now, what should be researched, build-planned, or verified next?

It does not execute the answer.

## Inputs

The planner consumes:

- live schema fingerprint;
- latest command-center snapshot hash;
- active agents and roles;
- active portfolio initiatives;
- unresolved portfolio data gaps;
- open agent goals.

The source database remains authoritative. The planner never backfills missing facts.

## Work classes

- `VERIFY`: close a gap with authoritative evidence.
- `RESEARCH`: answer an unresolved analytical question.
- `BUILD`: produce an evidence-backed implementation/remaining-work plan. In this phase BUILD is
  planning-only and does not modify repositories or production systems.

## Hunter routing

Hunter eligibility is fail-closed.

A work item enters the Hunter queue only when its required source type is explicitly technical and
public, such as `PUBLIC_GITHUB`, `PUBLIC_CODE`, `OPEN_SOURCE`, `REPOSITORY`, or
`TECHNICAL_IMPLEMENTATION`.

Finance, CRM, customer-response, private analytics, ledger and manual-record gaps never become
Hunter assignments merely because they are high priority.

A Hunter-eligible item is still **pre-verification scheduling evidence only**. It must enter the
existing Worker Runbook assignment/claim/lease path before any Hunter performs work.

## Authority boundary

Every generated work item is:

- `planning_only = true`;
- `external_write_allowed = false`;
- subject to human approval for any later external write.

The planner cannot create goals, acquire leases, emit READY/CLAIM/START/COMPLETE events, send
messages, open pull requests, deploy code, spend money, approve requests, or alter Supabase.

## Determinism and provenance

Each work item receives a stable identity hash derived from initiative + metric + gap + source
contract. The full packet receives a plan hash bound to the live schema fingerprint and
command-center snapshot hash.

Existing goals are surfaced only as possible overlap signals. The planner does not silently mark a
gap resolved because a goal exists.
