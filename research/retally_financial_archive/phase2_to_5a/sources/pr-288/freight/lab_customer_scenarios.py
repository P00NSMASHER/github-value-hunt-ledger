"""Deterministic, hypothetical customer reactions to tested lab events.

No messages are sent. Thresholds are explicit assumptions, not behavioral
estimates learned from real RETALLY customers.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

from freight.lab_operations_intelligence import JourneyEvent
from freight.lab_assurance import AssuranceRejected, digest


@dataclass(frozen=True)
class CustomerPersona:
    role: str
    expected_update_days: int
    refund_followup_days: int
    insists_on_credit_documents: bool


@dataclass(frozen=True)
class CustomerReaction:
    kind: str
    modeled_trigger: str
    evidence_event_id: str
    wait_days: int
    simulation_only: bool = True


def _date(time_string: str) -> datetime:
    try:
        value = datetime.fromisoformat(time_string.replace("Z", "+00:00"))
    except ValueError as ex:
        raise AssuranceRejected("INVALID_CUSTOMER_EVENT_TIME") from ex
    if value.tzinfo is None or value.utcoffset() is None:
        raise AssuranceRejected("INVALID_CUSTOMER_EVENT_TIME")
    return value.astimezone(timezone.utc)


def simulate_customer_reactions(events: Sequence[JourneyEvent], persona: CustomerPersona,
                                *, refund_due_cents: int, as_of: str) -> dict:
    if not events or not persona.role or type(persona.insists_on_credit_documents) is not bool:
        raise ValueError("persona and events required")
    if any(type(x) is not int or x<=0 for x in (persona.expected_update_days, persona.refund_followup_days)):
        raise ValueError("response thresholds must be positive integer days")
    if type(refund_due_cents) is not int or refund_due_cents < 0:
        raise ValueError("refund_due_cents must be nonnegative integer")
    now=_date(as_of)
    if any(_date(ev.occurred_at)>now for ev in events):
        raise AssuranceRejected("CUSTOMER_SIMULATION_FUTURE_EVENT")
    reversed_events=[ev for ev in events if ev.stage=="CREDIT_REVERSED"]
    updates=[ev for ev in events if ev.stage=="CUSTOMER_UPDATED"]
    credit=[ev for ev in events if ev.stage=="CREDIT_ALLOCATED"]
    reactions=[]
    if not updates:
        raise AssuranceRejected("CUSTOMER_SIMULATION_NO_COMMUNICATION_EVENT")
    latest=max(updates,key=lambda x:_date(x.occurred_at))
    days=(now-_date(latest.occurred_at)).days
    if days>=persona.expected_update_days:
        reactions.append(CustomerReaction("REQUEST_STATUS_UPDATE",
            "no modeled update within configured threshold",latest.event_id,days))
    if persona.insists_on_credit_documents and credit:
        first=min(credit,key=lambda x:_date(x.occurred_at))
        reactions.append(CustomerReaction("REQUEST_CREDIT_DOCUMENTATION",
            "persona policy requires carrier credit documentation",first.event_id,0))
    if reversed_events and refund_due_cents>0:
        last=max(reversed_events,key=lambda x:_date(x.occurred_at))
        wait=(now-_date(last.occurred_at)).days
        if wait>=persona.refund_followup_days:
            reactions.append(CustomerReaction("ESCALATE_REFUND_UNRESOLVED",
                "a reversed credit has an open synthetic fee refund liability",last.event_id,wait))
    body={"schema":1,"scope":"HYPOTHETICAL_PERSONA_NOT_MEASURED",
          "persona":asdict(persona),"as_of":as_of,
          "reactions":[asdict(x) for x in reactions]}
    body["receipt_hash"]=digest(body)
    return body
