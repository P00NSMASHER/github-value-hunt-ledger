"""Machine-checkable charter for optional fixed-fee Freight Recovery work.

The charter freezes the commercial/delivery handoff around an already-generated
legacy/custom Pilot Activation Packet. The flagship success-based path uses
``freight.recovery_engagement``. This is an operational acknowledgment record,
not an e-signature system or legal contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from pathlib import Path

SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
PRICE_RE=re.compile(r"\$([0-9,]+).*?\$([0-9,]+)")

class CharterState(str,Enum):
    PENDING_ACKNOWLEDGMENT="PENDING_ACKNOWLEDGMENT"
    PRELAUNCH_ACCEPTED="PRELAUNCH_ACCEPTED"
    KICKOFF_AUTHORIZED="KICKOFF_AUTHORIZED"

@dataclass(frozen=True)
class CharterRequest:
    engagement_id:str
    buyer_id:str
    business_unit:str
    population_rule:str
    source_date_start:str
    source_date_end:str
    carrier_scope:tuple[str,...]
    mode_scope:tuple[str,...]
    fixed_fee_usd:float
    buyer_truth_owner_role:str
    buyer_action_approver_role:str
    freight_engagement_owner_role:str
    buyer_acknowledges_scope:bool
    buyer_acknowledges_blind_protocol:bool
    buyer_acknowledges_report_totals_separate:bool
    buyer_acknowledges_no_guaranteed_recovery:bool
    freight_acknowledges_no_external_action_without_buyer_approval:bool

@dataclass(frozen=True)
class PilotCharter:
    charter_state:str
    engagement_id:str
    buyer_id:str
    business_unit:str
    activation_hash:str
    launch_status:str
    launch_route:str
    selected_offer:str
    price_band_usd:str
    fixed_fee_usd:float
    population_rule:str
    source_date_start:str
    source_date_end:str
    carrier_scope:tuple[str,...]
    mode_scope:tuple[str,...]
    buyer_truth_owner_role:str
    buyer_action_approver_role:str
    freight_engagement_owner_role:str
    customer_data_authorized:bool
    external_action_authorized:bool
    external_action_policy:str
    acknowledgments:dict
    charter_hash:str

def _canonical_hash(value:object)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _required(name:str,value:str)->None:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+" is required")

def _parse_price_band(value:str)->tuple[float,float]|None:
    """Parse legacy explicit bands; new custom-scoped packets intentionally omit one."""
    m=PRICE_RE.search(value or "")
    if not m:
        return None
    low=float(m.group(1).replace(",",""))
    high=float(m.group(2).replace(",",""))
    if low<=0 or high<low:
        raise ValueError("activation packet price band is invalid")
    return low,high

def _validate_activation_packet(packet:dict)->None:
    digest=packet.get("activation_hash")
    if not isinstance(digest,str) or not SHA256_RE.fullmatch(digest):
        raise ValueError("activation_hash must be lowercase SHA-256")
    body={k:v for k,v in packet.items() if k!="activation_hash"}
    if _canonical_hash(body)!=digest:
        raise ValueError("activation packet hash mismatch")
    if packet.get("launch_status") not in {"BLOCKED","CONDITIONAL","READY"}:
        raise ValueError("activation packet launch_status invalid")
    _required("selected_offer",packet.get("selected_offer"))
    _required("launch_route",packet.get("launch_route"))
    _required("price_band_usd",packet.get("price_band_usd"))

def _parse_date(name:str,value:str)->date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(name+" must be ISO date YYYY-MM-DD") from exc

def from_dict(data:dict)->CharterRequest:
    fields=CharterRequest.__dataclass_fields__
    missing=[k for k in fields if k not in data]
    if missing:
        raise ValueError("missing charter fields: "+", ".join(missing))
    extra=sorted(set(data)-set(fields))
    if extra:
        raise ValueError("unknown charter fields: "+", ".join(extra))
    normalized=dict(data)
    normalized["carrier_scope"]=tuple(data["carrier_scope"])
    normalized["mode_scope"]=tuple(data["mode_scope"])
    return CharterRequest(**normalized)

def build_charter(activation_packet:dict,request:CharterRequest)->PilotCharter:
    _validate_activation_packet(activation_packet)
    for name in ("engagement_id","buyer_id","business_unit","population_rule","buyer_truth_owner_role","buyer_action_approver_role","freight_engagement_owner_role"):
        _required(name,getattr(request,name))
    start=_parse_date("source_date_start",request.source_date_start)
    end=_parse_date("source_date_end",request.source_date_end)
    if end<start:
        raise ValueError("source_date_end cannot precede source_date_start")
    if not request.carrier_scope or any(not isinstance(x,str) or not x.strip() for x in request.carrier_scope):
        raise ValueError("carrier_scope must contain at least one non-empty carrier")
    if not request.mode_scope or any(not isinstance(x,str) or not x.strip() for x in request.mode_scope):
        raise ValueError("mode_scope must contain at least one non-empty mode")
    if request.fixed_fee_usd<=0:
        raise ValueError("fixed_fee_usd must be positive")
    published_band=_parse_price_band(activation_packet["price_band_usd"])
    if published_band is not None:
        low,high=published_band
        if not low<=request.fixed_fee_usd<=high:
            raise ValueError("fixed_fee_usd outside activation-packet published price band")

    acknowledgments={
        "buyer_acknowledges_scope":request.buyer_acknowledges_scope,
        "buyer_acknowledges_blind_protocol":request.buyer_acknowledges_blind_protocol,
        "buyer_acknowledges_report_totals_separate":request.buyer_acknowledges_report_totals_separate,
        "buyer_acknowledges_no_guaranteed_recovery":request.buyer_acknowledges_no_guaranteed_recovery,
        "freight_acknowledges_no_external_action_without_buyer_approval":request.freight_acknowledges_no_external_action_without_buyer_approval,
    }
    all_ack=all(acknowledgments.values())
    launch_ready=activation_packet["launch_status"]=="READY"
    if all_ack and launch_ready:
        state=CharterState.KICKOFF_AUTHORIZED
    elif all_ack:
        state=CharterState.PRELAUNCH_ACCEPTED
    else:
        state=CharterState.PENDING_ACKNOWLEDGMENT

    body={
        "charter_state":state.value,
        "engagement_id":request.engagement_id,
        "buyer_id":request.buyer_id,
        "business_unit":request.business_unit,
        "activation_hash":activation_packet["activation_hash"],
        "launch_status":activation_packet["launch_status"],
        "launch_route":activation_packet["launch_route"],
        "selected_offer":activation_packet["selected_offer"],
        "price_band_usd":activation_packet["price_band_usd"],
        "fixed_fee_usd":round(float(request.fixed_fee_usd),2),
        "population_rule":request.population_rule,
        "source_date_start":request.source_date_start,
        "source_date_end":request.source_date_end,
        "carrier_scope":list(request.carrier_scope),
        "mode_scope":list(request.mode_scope),
        "buyer_truth_owner_role":request.buyer_truth_owner_role,
        "buyer_action_approver_role":request.buyer_action_approver_role,
        "freight_engagement_owner_role":request.freight_engagement_owner_role,
        "customer_data_authorized":state is CharterState.KICKOFF_AUTHORIZED,
        "external_action_authorized":False,
        "external_action_policy":"SEPARATE_BUYER_APPROVAL_REQUIRED",
        "acknowledgments":acknowledgments,
    }
    return PilotCharter(
        state.value,request.engagement_id,request.buyer_id,request.business_unit,
        activation_packet["activation_hash"],activation_packet["launch_status"],
        activation_packet["launch_route"],activation_packet["selected_offer"],
        activation_packet["price_band_usd"],round(float(request.fixed_fee_usd),2),
        request.population_rule,request.source_date_start,request.source_date_end,
        request.carrier_scope,request.mode_scope,request.buyer_truth_owner_role,
        request.buyer_action_approver_role,request.freight_engagement_owner_role,
        state is CharterState.KICKOFF_AUTHORIZED,False,
        "SEPARATE_BUYER_APPROVAL_REQUIRED",acknowledgments,_canonical_hash(body)
    )

def render_markdown(charter:PilotCharter)->str:
    lines=["# Freight Recovery — Pilot Charter","",
        f"**State:** {charter.charter_state}",
        f"**Engagement:** `{charter.engagement_id}`",
        f"**Buyer / BU:** `{charter.buyer_id}` / `{charter.business_unit}`",
        f"**Offer:** {charter.selected_offer}",
        f"**Fixed fee:** ${charter.fixed_fee_usd:,.2f}",
        f"**Launch status / route:** {charter.launch_status} / {charter.launch_route}",
        f"**Activation hash:** `{charter.activation_hash}`",
        f"**Charter hash:** `{charter.charter_hash}`","",
        "## Frozen scope","",
        f"- Population rule: {charter.population_rule}",
        f"- Source dates: {charter.source_date_start} through {charter.source_date_end}",
        "- Carriers: "+", ".join(charter.carrier_scope),
        "- Modes: "+", ".join(charter.mode_scope),"",
        "## Named operating roles","",
        f"- Buyer truth owner: {charter.buyer_truth_owner_role}",
        f"- Buyer action approver: {charter.buyer_action_approver_role}",
        f"- Freight engagement owner: {charter.freight_engagement_owner_role}","",
        "## Authorization boundary","",
        f"- Customer data authorized for kickoff: **{str(charter.customer_data_authorized).lower()}**",
        "- Carrier/vendor contact or money-moving action authorized by this charter: **false**",
        "- External-action policy: separate buyer approval required.","",
        "## Acknowledgments",""]
    for key,value in charter.acknowledgments.items():
        lines.append(f"- {key}: **{str(value).lower()}**")
    lines.extend(["",
        "This charter is an operational scope-freeze and acknowledgment artifact. It is not an e-signature system, legal advice, or a substitute for the governing commercial agreement.",""] )
    return "\n".join(lines)

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("activation_packet_json")
    parser.add_argument("charter_request_json")
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    packet=json.loads(Path(args.activation_packet_json).read_text(encoding="utf-8"))
    request=from_dict(json.loads(Path(args.charter_request_json).read_text(encoding="utf-8")))
    charter=build_charter(packet,request)
    if args.format=="json":
        print(json.dumps(asdict(charter),indent=2,ensure_ascii=False))
    else:
        print(render_markdown(charter))

if __name__=="__main__":
    main()
