"""Fail-closed change control for a frozen Freight Recovery Pilot Charter.

The amendment record never mutates a Charter in place. Accepted changes require
a replacement Charter. Material scope changes additionally require a new
activation/launch decision before the replacement can become operative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
PRICE_RE=re.compile(r"\$([0-9,]+).*?\$([0-9,]+)")

class AmendmentState(str,Enum):
    PENDING_ACKNOWLEDGMENT="PENDING_ACKNOWLEDGMENT"
    ACCEPTED_REPLACEMENT_REQUIRED="ACCEPTED_REPLACEMENT_REQUIRED"
    SUPERSEDED_BY_REPLACEMENT="SUPERSEDED_BY_REPLACEMENT"

@dataclass(frozen=True)
class AmendmentRequest:
    amendment_id:str
    reason:str
    buyer_acknowledges_change:bool
    freight_acknowledges_change:bool
    population_rule:str|None=None
    source_date_start:str|None=None
    source_date_end:str|None=None
    carrier_scope:tuple[str,...]|None=None
    mode_scope:tuple[str,...]|None=None
    fixed_fee_usd:float|None=None
    buyer_truth_owner_role:str|None=None
    buyer_action_approver_role:str|None=None
    freight_engagement_owner_role:str|None=None

@dataclass(frozen=True)
class PilotAmendment:
    amendment_state:str
    amendment_id:str
    engagement_id:str
    base_charter_hash:str
    replacement_charter_hash:str|None
    changed_fields:tuple[str,...]
    requires_readiness_revalidation:bool
    requires_launch_revalidation:bool
    requires_new_activation:bool
    requires_reacknowledgment:bool
    kickoff_suspended:bool
    customer_data_authorized:bool
    external_action_authorized:bool
    external_action_policy:str
    amendment_hash:str

MATERIAL_SCOPE_FIELDS={"population_rule","source_date_start","source_date_end","carrier_scope","mode_scope"}
ROLE_FIELDS={"buyer_truth_owner_role","buyer_action_approver_role","freight_engagement_owner_role"}

def _hash(value:object)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _required(name:str,value:str)->None:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+" is required")

def _verify_charter(charter:dict)->None:
    digest=charter.get("charter_hash")
    if not isinstance(digest,str) or not SHA256_RE.fullmatch(digest):
        raise ValueError("charter_hash must be lowercase SHA-256")
    body={k:v for k,v in charter.items() if k!="charter_hash"}
    if _hash(body)!=digest:
        raise ValueError("charter hash mismatch")
    for key in ("engagement_id","buyer_id","business_unit","activation_hash","price_band_usd"):
        _required(key,charter.get(key))
    if charter.get("external_action_authorized") is not False:
        raise ValueError("base Charter external_action_authorized must be false")

def _price_band(value:str)->tuple[float,float]:
    m=PRICE_RE.search(value or "")
    if not m:
        raise ValueError("price band is not parseable")
    return float(m.group(1).replace(",","")),float(m.group(2).replace(",",""))

def from_dict(data:dict)->AmendmentRequest:
    fields=AmendmentRequest.__dataclass_fields__
    missing=[k for k in ("amendment_id","reason","buyer_acknowledges_change","freight_acknowledges_change") if k not in data]
    if missing:
        raise ValueError("missing amendment fields: "+", ".join(missing))
    extra=sorted(set(data)-set(fields))
    if extra:
        raise ValueError("unknown amendment fields: "+", ".join(extra))
    normalized=dict(data)
    if "carrier_scope" in normalized and normalized["carrier_scope"] is not None:
        normalized["carrier_scope"]=tuple(normalized["carrier_scope"])
    if "mode_scope" in normalized and normalized["mode_scope"] is not None:
        normalized["mode_scope"]=tuple(normalized["mode_scope"])
    return AmendmentRequest(**normalized)

def _proposed(request:AmendmentRequest)->dict:
    return {
        field:getattr(request,field)
        for field in (
            "population_rule","source_date_start","source_date_end","carrier_scope","mode_scope",
            "fixed_fee_usd","buyer_truth_owner_role","buyer_action_approver_role","freight_engagement_owner_role"
        )
        if getattr(request,field) is not None
    }

def _normalize(value):
    if isinstance(value,tuple):
        return list(value)
    return value

def build_amendment(base_charter:dict,request:AmendmentRequest,replacement_charter:dict|None=None)->PilotAmendment:
    _verify_charter(base_charter)
    _required("amendment_id",request.amendment_id)
    _required("reason",request.reason)
    proposed=_proposed(request)
    changed={k:v for k,v in proposed.items() if _normalize(base_charter.get(k))!=_normalize(v)}
    if not changed:
        raise ValueError("amendment must change at least one Charter field")

    if "fixed_fee_usd" in changed:
        fee=float(changed["fixed_fee_usd"])
        if fee<=0:
            raise ValueError("fixed_fee_usd must be positive")
    for key in ("carrier_scope","mode_scope"):
        if key in changed and (not changed[key] or any(not isinstance(x,str) or not x.strip() for x in changed[key])):
            raise ValueError(key+" must contain at least one non-empty value")

    changed_fields=tuple(sorted(changed))
    material=bool(MATERIAL_SCOPE_FIELDS.intersection(changed))
    role_change=bool(ROLE_FIELDS.intersection(changed))
    fee_change="fixed_fee_usd" in changed
    low,high=_price_band(base_charter["price_band_usd"])
    fee_outside_band=fee_change and not (low<=float(changed["fixed_fee_usd"])<=high)

    requires_readiness=material
    requires_launch=material
    requires_new_activation=material or fee_outside_band
    requires_reack=material or role_change or fee_change
    accepted=request.buyer_acknowledges_change and request.freight_acknowledges_change

    replacement_hash=None
    customer_data_authorized=False
    state=AmendmentState.PENDING_ACKNOWLEDGMENT
    kickoff_suspended=False
    if accepted:
        state=AmendmentState.ACCEPTED_REPLACEMENT_REQUIRED
        kickoff_suspended=True

    if replacement_charter is not None:
        if not accepted:
            raise ValueError("replacement Charter cannot be accepted before amendment acknowledgments")
        _verify_charter(replacement_charter)
        if replacement_charter["engagement_id"]!=base_charter["engagement_id"]:
            raise ValueError("replacement Charter engagement_id mismatch")
        if replacement_charter["buyer_id"]!=base_charter["buyer_id"] or replacement_charter["business_unit"]!=base_charter["business_unit"]:
            raise ValueError("buyer/business-unit changes require a new engagement, not an amendment")
        for key,value in changed.items():
            if _normalize(replacement_charter.get(key))!=_normalize(value):
                raise ValueError("replacement Charter does not reflect amended field: "+key)
        protected=("population_rule","source_date_start","source_date_end","carrier_scope","mode_scope","fixed_fee_usd","buyer_truth_owner_role","buyer_action_approver_role","freight_engagement_owner_role")
        for key in protected:
            if key not in changed and _normalize(replacement_charter.get(key))!=_normalize(base_charter.get(key)):
                raise ValueError("replacement Charter changed unapproved field: "+key)
        if requires_new_activation and replacement_charter["activation_hash"]==base_charter["activation_hash"]:
            raise ValueError("material/out-of-band amendment requires a new Activation Packet")
        if fee_outside_band and replacement_charter["price_band_usd"]==base_charter["price_band_usd"]:
            raise ValueError("out-of-band fee amendment requires a new published price band")
        replacement_hash=replacement_charter["charter_hash"]
        state=AmendmentState.SUPERSEDED_BY_REPLACEMENT
        kickoff_suspended=not bool(replacement_charter.get("customer_data_authorized"))
        customer_data_authorized=bool(replacement_charter.get("customer_data_authorized"))

    body={
        "amendment_state":state.value,
        "amendment_id":request.amendment_id,
        "engagement_id":base_charter["engagement_id"],
        "base_charter_hash":base_charter["charter_hash"],
        "replacement_charter_hash":replacement_hash,
        "changed_fields":list(changed_fields),
        "requires_readiness_revalidation":requires_readiness,
        "requires_launch_revalidation":requires_launch,
        "requires_new_activation":requires_new_activation,
        "requires_reacknowledgment":requires_reack,
        "kickoff_suspended":kickoff_suspended,
        "customer_data_authorized":customer_data_authorized,
        "external_action_authorized":False,
        "external_action_policy":"SEPARATE_BUYER_APPROVAL_REQUIRED",
    }
    return PilotAmendment(
        state.value,request.amendment_id,base_charter["engagement_id"],base_charter["charter_hash"],
        replacement_hash,changed_fields,requires_readiness,requires_launch,requires_new_activation,
        requires_reack,kickoff_suspended,customer_data_authorized,False,
        "SEPARATE_BUYER_APPROVAL_REQUIRED",_hash(body)
    )

def render_markdown(amendment:PilotAmendment)->str:
    lines=["# Freight Recovery — Pilot Amendment","",
        f"**State:** {amendment.amendment_state}",
        f"**Amendment:** `{amendment.amendment_id}`",
        f"**Engagement:** `{amendment.engagement_id}`",
        f"**Base Charter:** `{amendment.base_charter_hash}`",
        f"**Replacement Charter:** `{amendment.replacement_charter_hash or 'pending'}`",
        f"**Amendment hash:** `{amendment.amendment_hash}`","",
        "## Revalidation","",
        f"- Changed fields: {", ".join(amendment.changed_fields)}",
        f"- Readiness revalidation required: **{str(amendment.requires_readiness_revalidation).lower()}**",
        f"- Launch revalidation required: **{str(amendment.requires_launch_revalidation).lower()}**",
        f"- New Activation Packet required: **{str(amendment.requires_new_activation).lower()}**",
        f"- Re-acknowledgment required: **{str(amendment.requires_reacknowledgment).lower()}**","",
        "## Authorization boundary","",
        f"- Kickoff suspended pending replacement: **{str(amendment.kickoff_suspended).lower()}**",
        f"- Customer data authorized by this amendment: **{str(amendment.customer_data_authorized).lower()}**",
        "- External carrier/vendor action authorized by this amendment: **false**",
        "- External-action policy: separate buyer approval required.","",
        "The original Charter remains immutable. This amendment becomes operative only through a validated replacement Charter.",""]
    return "\n".join(lines)

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("base_charter_json")
    parser.add_argument("amendment_request_json")
    parser.add_argument("--replacement-charter-json")
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    base=json.loads(Path(args.base_charter_json).read_text(encoding="utf-8"))
    request=from_dict(json.loads(Path(args.amendment_request_json).read_text(encoding="utf-8")))
    replacement=json.loads(Path(args.replacement_charter_json).read_text(encoding="utf-8")) if args.replacement_charter_json else None
    amendment=build_amendment(base,request,replacement)
    if args.format=="json":
        print(json.dumps(asdict(amendment),indent=2,ensure_ascii=False))
    else:
        print(render_markdown(amendment))

if __name__=="__main__":
    main()