"""Resolve the authoritative operating state of a Freight Recovery engagement.

Charters and Amendments remain immutable. This module derives which Charter is
currently effective for execution and whether downstream customer-data work is
allowed.
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

class EngagementState(str,Enum):
    PRELAUNCH="PRELAUNCH"
    ACTIVE="ACTIVE"
    PRELAUNCH_WITH_PENDING_AMENDMENT="PRELAUNCH_WITH_PENDING_AMENDMENT"
    ACTIVE_WITH_PENDING_AMENDMENT="ACTIVE_WITH_PENDING_AMENDMENT"
    SUSPENDED_PENDING_REPLACEMENT="SUSPENDED_PENDING_REPLACEMENT"

@dataclass(frozen=True)
class EngagementResolution:
    engagement_state:str
    engagement_id:str
    buyer_id:str
    business_unit:str
    operative_charter_hash:str
    amendment_id:str|None
    amendment_hash:str|None
    replacement_required:bool
    customer_data_authorized:bool
    audit_processing_allowed:bool
    report_generation_allowed:bool
    settlement_processing_allowed:bool
    external_action_authorized:bool
    external_action_policy:str
    resolution_path:tuple[str,...]
    resolution_hash:str

def _hash(value:object)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _verify_hash(obj:dict,field:str,label:str)->None:
    digest=obj.get(field)
    if not isinstance(digest,str) or not SHA256_RE.fullmatch(digest):
        raise ValueError(label+" "+field+" must be lowercase SHA-256")
    body={k:v for k,v in obj.items() if k!=field}
    if _hash(body)!=digest:
        raise ValueError(label+" hash mismatch")

def _verify_charter(charter:dict)->None:
    _verify_hash(charter,"charter_hash","Charter")
    for key in ("engagement_id","buyer_id","business_unit","charter_state","external_action_policy"):
        value=charter.get(key)
        if not isinstance(value,str) or not value.strip():
            raise ValueError("Charter "+key+" is required")
    if charter.get("external_action_authorized") is not False:
        raise ValueError("Charter external_action_authorized must be false")
    authorized=bool(charter.get("customer_data_authorized"))
    if authorized and charter.get("charter_state")!="KICKOFF_AUTHORIZED":
        raise ValueError("customer_data_authorized requires KICKOFF_AUTHORIZED Charter")

def _verify_amendment(amendment:dict)->None:
    _verify_hash(amendment,"amendment_hash","Amendment")
    for key in ("amendment_id","engagement_id","base_charter_hash","amendment_state","external_action_policy"):
        value=amendment.get(key)
        if not isinstance(value,str) or not value.strip():
            raise ValueError("Amendment "+key+" is required")
    if amendment.get("external_action_authorized") is not False:
        raise ValueError("Amendment external_action_authorized must be false")
    state=amendment["amendment_state"]
    if state not in {"PENDING_ACKNOWLEDGMENT","ACCEPTED_REPLACEMENT_REQUIRED","SUPERSEDED_BY_REPLACEMENT"}:
        raise ValueError("invalid Amendment state")
    replacement=amendment.get("replacement_charter_hash")
    if state=="SUPERSEDED_BY_REPLACEMENT":
        if not isinstance(replacement,str) or not SHA256_RE.fullmatch(replacement):
            raise ValueError("SUPERSEDED amendment requires replacement_charter_hash")
    elif replacement is not None:
        raise ValueError("non-superseded amendment cannot have replacement_charter_hash")
    if state=="ACCEPTED_REPLACEMENT_REQUIRED" and amendment.get("kickoff_suspended") is not True:
        raise ValueError("accepted amendment must suspend kickoff")

def resolve_engagement(base_charter:dict,amendments:list[dict]|tuple[dict,...]=(),replacement_charters:list[dict]|tuple[dict,...]=())->EngagementResolution:
    _verify_charter(base_charter)
    charter_by_hash={base_charter["charter_hash"]:base_charter}
    for charter in replacement_charters:
        _verify_charter(charter)
        if charter["charter_hash"] in charter_by_hash:
            raise ValueError("duplicate Charter hash")
        if charter["engagement_id"]!=base_charter["engagement_id"]:
            raise ValueError("replacement Charter engagement_id mismatch")
        if charter["buyer_id"]!=base_charter["buyer_id"] or charter["business_unit"]!=base_charter["business_unit"]:
            raise ValueError("replacement Charter buyer/business-unit mismatch")
        charter_by_hash[charter["charter_hash"]]=charter

    amendment_by_base={}
    seen_amendment_hashes=set()
    for amendment in amendments:
        _verify_amendment(amendment)
        if amendment["amendment_hash"] in seen_amendment_hashes:
            raise ValueError("duplicate Amendment hash")
        seen_amendment_hashes.add(amendment["amendment_hash"])
        if amendment["engagement_id"]!=base_charter["engagement_id"]:
            raise ValueError("Amendment engagement_id mismatch")
        base_hash=amendment["base_charter_hash"]
        if base_hash in amendment_by_base:
            raise ValueError("multiple Amendments reference the same base Charter")
        amendment_by_base[base_hash]=amendment

    current=base_charter
    visited=set()
    path=[current["charter_hash"]]
    active_amendment=None

    while True:
        current_hash=current["charter_hash"]
        if current_hash in visited:
            raise ValueError("Charter/Amendment cycle detected")
        visited.add(current_hash)
        amendment=amendment_by_base.get(current_hash)
        if amendment is None:
            break
        active_amendment=amendment
        state=amendment["amendment_state"]
        path.append(amendment["amendment_hash"])
        if state=="SUPERSEDED_BY_REPLACEMENT":
            replacement_hash=amendment["replacement_charter_hash"]
            replacement=charter_by_hash.get(replacement_hash)
            if replacement is None:
                raise ValueError("replacement Charter hash is not supplied")
            current=replacement
            path.append(current["charter_hash"])
            continue
        break

    charter_authorized=bool(current.get("customer_data_authorized"))
    state=current.get("charter_state")
    amendment=active_amendment

    if amendment and amendment["base_charter_hash"]==current["charter_hash"]:
        astate=amendment["amendment_state"]
        if astate=="ACCEPTED_REPLACEMENT_REQUIRED":
            engagement_state=EngagementState.SUSPENDED_PENDING_REPLACEMENT
            authorized=False
            replacement_required=True
        elif astate=="PENDING_ACKNOWLEDGMENT":
            engagement_state=(EngagementState.ACTIVE_WITH_PENDING_AMENDMENT if charter_authorized else EngagementState.PRELAUNCH_WITH_PENDING_AMENDMENT)
            authorized=charter_authorized
            replacement_required=False
        else:
            raise AssertionError("resolver stopped unexpectedly on superseded amendment")
    else:
        engagement_state=EngagementState.ACTIVE if charter_authorized else EngagementState.PRELAUNCH
        authorized=charter_authorized
        replacement_required=False

    current_amendment=(
        amendment
        if amendment is not None
        and amendment["base_charter_hash"]==current["charter_hash"]
        and amendment["amendment_state"]!="SUPERSEDED_BY_REPLACEMENT"
        else None
    )

    body={
        "engagement_state":engagement_state.value,
        "engagement_id":current["engagement_id"],
        "buyer_id":current["buyer_id"],
        "business_unit":current["business_unit"],
        "operative_charter_hash":current["charter_hash"],
        "amendment_id":current_amendment["amendment_id"] if current_amendment else None,
        "amendment_hash":current_amendment["amendment_hash"] if current_amendment else None,
        "replacement_required":replacement_required,
        "customer_data_authorized":authorized,
        "audit_processing_allowed":authorized,
        "report_generation_allowed":authorized,
        "settlement_processing_allowed":authorized,
        "external_action_authorized":False,
        "external_action_policy":"SEPARATE_BUYER_APPROVAL_REQUIRED",
        "resolution_path":path,
    }
    return EngagementResolution(
        engagement_state.value,current["engagement_id"],current["buyer_id"],current["business_unit"],
        current["charter_hash"],body["amendment_id"],body["amendment_hash"],replacement_required,
        authorized,authorized,authorized,authorized,False,"SEPARATE_BUYER_APPROVAL_REQUIRED",
        tuple(path),_hash(body)
    )

def render_markdown(resolution:EngagementResolution)->str:
    lines=["# Freight Recovery — Engagement State","",
        f"**State:** {resolution.engagement_state}",
        f"**Engagement:** `{resolution.engagement_id}`",
        f"**Buyer / BU:** `{resolution.buyer_id}` / `{resolution.business_unit}`",
        f"**Operative Charter:** `{resolution.operative_charter_hash}`",
        f"**Resolution hash:** `{resolution.resolution_hash}`","",
        "## Execution authorization","",
        f"- Customer data authorized: **{str(resolution.customer_data_authorized).lower()}**",
        f"- Audit processing allowed: **{str(resolution.audit_processing_allowed).lower()}**",
        f"- Report generation allowed: **{str(resolution.report_generation_allowed).lower()}**",
        f"- Settlement processing allowed: **{str(resolution.settlement_processing_allowed).lower()}**",
        "- External carrier/vendor action authorized: **false**",
        "- External-action policy: separate buyer approval required.","",
        "## Amendment state","",
        f"- Amendment ID: `{resolution.amendment_id or 'none'}`",
        f"- Replacement required: **{str(resolution.replacement_required).lower()}**","",
        "Resolution path:",""]
    lines.extend("- `"+item+"`" for item in resolution.resolution_path)
    lines.extend(["",
        "Downstream systems should require this resolver rather than inferring authorization from the newest-looking Charter or Amendment file.",""] )
    return "\n".join(lines)

def _load(path:str)->dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _load_list(path:str|None)->list[dict]:
    if not path:
        return []
    value=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value,list):
        raise ValueError("expected a JSON array")
    return value

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("base_charter_json")
    parser.add_argument("--amendments-json")
    parser.add_argument("--replacement-charters-json")
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    resolution=resolve_engagement(_load(args.base_charter_json),_load_list(args.amendments_json),_load_list(args.replacement_charters_json))
    if args.format=="json":
        print(json.dumps(asdict(resolution),indent=2,ensure_ascii=False))
    else:
        print(render_markdown(resolution))

if __name__=="__main__":
    main()