"""Deterministic buyer-safe Pilot Activation Packet for Freight Recovery."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from freight.launch_brief import build_brief
from freight.readiness import assess_readiness, from_dict

@dataclass(frozen=True)
class DataRequest:
    timing:str
    category:str
    source_type:str|None
    requirement:str

@dataclass(frozen=True)
class ActivationPacket:
    readiness_status:str
    readiness_score:int
    selected_offer:str
    offer_name:str
    price_band_usd:str
    target_turnaround:str|None
    launch_status:str
    launch_route:str
    remediation_actions:tuple[dict,...]
    buyer_data_requests:tuple[DataRequest,...]
    buyer_responsibilities:tuple[str,...]
    freight_responsibilities:tuple[str,...]
    protocol_stages:tuple[str,...]
    buyer_report_totals:tuple[str,...]
    commercial_invariants:tuple[str,...]
    activation_hash:str

OFFER_CATALOG={
    "DATA_READINESS_DIAGNOSTIC": {
        "name":"Data Readiness / Authority Diagnostic",
        "price_band_usd":"$5,000–$7,500 fixed",
        "turnaround":None,
    },
    "BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST": {
        "name":"Blind Freight Audit Acceptance Test",
        "price_band_usd":"$15,000–$25,000 fixed",
        "turnaround":"10–15 business days after complete inputs",
    },
}

COMMON_REQUESTS=(
    DataRequest("NOW","AUTHORIZATION",None,"Document buyer entity/business unit, approved date range, carriers/modes, source scope, retention and deletion terms."),
    DataRequest("NOW","INVOICE_ACTUALS","invoice","Provide invoice/EDI actuals for the candidate population, with stable invoice identifiers and source hashes."),
    DataRequest("NOW","COMMERCIAL_AUTHORITY","authority","Provide controlling contract/rate/rate-confirmation authority plus all effective amendments/addenda/tariff references."),
    DataRequest("NOW","IDENTITY","identity_map","Provide stable buyer/business-unit/carrier/shipment identity mapping where source systems do not already share stable identifiers."),
    DataRequest("CONDITIONAL","SHIPMENT_EVIDENCE","shipment_evidence","Provide BOL/POD/appointment/weight/telematics or other operational evidence when the supported rule requires it."),
    DataRequest("LATER_OUTCOME","SETTLEMENT","settlement_observation","Identify the buyer-controlled credit/refund/remittance/payment-adjustment source that can later prove realized outcomes."),
)

BLIND_ONLY=(
    DataRequest("NOW","INCUMBENT_OUTPUT","incumbent_output","Provide the incumbent audit/payment findings/output through a source that can remain sealed until buyer-owned truth is frozen."),
)

BUYER_RESPONSIBILITIES=(
    "Define the exact population selection rule and buyer/business-unit scope.",
    "Provide authorized read-only sources with no credentials/secrets embedded.",
    "Name the buyer-side truth owner and the person authorized to approve findings/actions.",
    "Keep incumbent output sealed until the truth freeze is complete.",
    "Provide later buyer-controlled settlement evidence for any claimed recovery.",
    "Approve any external carrier/vendor dispute or action before it occurs.",
)

FREIGHT_RESPONSIBILITIES=(
    "Build and hash the source/data-room manifest before truth-building.",
    "Freeze the population; any row change creates a new version.",
    "Seal the incumbent source against buyer/BU + population before truth freeze.",
    "Freeze buyer-owned truth before opening the incumbent output.",
    "Independently reproduce expected charges and keep ambiguous cases REVIEW / $0.",
    "Compare challenger vs incumbent on finding identity, reason and dollars.",
    "Separate discrepancy, validated, challenger-only validated and realized totals.",
    "Perform no carrier/vendor contact or money-moving action without buyer approval.",
)

PROTOCOL_STAGES=(
    "0 — Buyer authorization and scope",
    "1 — Data-readiness gate",
    "2 — Freeze population and seal incumbent source",
    "3 — Freeze buyer-owned truth",
    "4 — Open incumbent output and compare blind",
    "5 — Buyer review and approved action",
    "6 — Settlement readback",
    "7 — Final pilot-package integrity hash",
)

REPORT_TOTALS=(
    "reviewed discrepancy dollars",
    "validated finding dollars",
    "challenger-only validated dollars",
    "uniquely attributable realized dollars",
)

COMMERCIAL_INVARIANTS=(
    "Discrepancy dollars are not recovery dollars.",
    "Missing or ambiguous authority, shipment identity or required evidence = REVIEW / $0.",
    "Ambiguous settlement allocation = $0 realized.",
    "Incumbent output stays sealed until buyer-owned truth is frozen.",
    "Customer data is read-only during the first pilot unless separately approved.",
    "No success fee on incumbent-known, automatic/preexisting, unresolved or duplicate recovery.",
)

def _hash(value:object)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def build_packet(readiness_input:dict, launch_decision:dict)->ActivationPacket:
    readiness=assess_readiness(from_dict(readiness_input))
    offer=OFFER_CATALOG[readiness.recommended_offer]
    brief=build_brief(launch_decision)
    requests=list(COMMON_REQUESTS)
    if readiness.recommended_offer=="BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST":
        requests.extend(BLIND_ONLY)
    requests=tuple(sorted(requests,key=lambda x:({"NOW":0,"CONDITIONAL":1,"LATER_OUTCOME":2}[x.timing],x.category,x.requirement)))
    actions=tuple(asdict(a) for a in brief.actions)
    body={
        "readiness_status":readiness.status.value,
        "readiness_score":readiness.score,
        "selected_offer":readiness.recommended_offer,
        "offer_name":offer["name"],
        "price_band_usd":offer["price_band_usd"],
        "target_turnaround":offer["turnaround"],
        "launch_status":brief.status,
        "launch_route":brief.route,
        "remediation_actions":actions,
        "buyer_data_requests":[asdict(x) for x in requests],
        "buyer_responsibilities":BUYER_RESPONSIBILITIES,
        "freight_responsibilities":FREIGHT_RESPONSIBILITIES,
        "protocol_stages":PROTOCOL_STAGES,
        "buyer_report_totals":REPORT_TOTALS,
        "commercial_invariants":COMMERCIAL_INVARIANTS,
    }
    return ActivationPacket(
        readiness.status.value,readiness.score,readiness.recommended_offer,
        offer["name"],offer["price_band_usd"],offer["turnaround"],
        brief.status,brief.route,actions,requests,BUYER_RESPONSIBILITIES,
        FREIGHT_RESPONSIBILITIES,PROTOCOL_STAGES,REPORT_TOTALS,
        COMMERCIAL_INVARIANTS,_hash(body)
    )

def render_markdown(packet:ActivationPacket)->str:
    lines=["# Freight Recovery — Pilot Activation Packet","",
        f"**Readiness:** {packet.readiness_status} ({packet.readiness_score}/100)",
        f"**Selected offer:** {packet.offer_name}",
        f"**Published price band:** {packet.price_band_usd}",
        f"**Launch status:** {packet.launch_status}",
        f"**Launch route:** {packet.launch_route}",
        f"**Activation hash:** `{packet.activation_hash}`",""]
    if packet.target_turnaround:
        lines.append(f"**Target analysis/report turnaround:** {packet.target_turnaround}")
        lines.append("")
    lines.extend(["## Launch remediation",""])
    if not packet.remediation_actions:
        lines.append("- No launch-gate remediation actions are currently required for the selected route.")
    else:
        for a in packet.remediation_actions:
            lines.append(f"- **[{a['priority']}] {a['title']}** — owner: {a['owner']}")
            for e in a["evidence_required"]:
                lines.append(f"  - Evidence: {e}")
    lines.extend(["","## Buyer data-room requests",""])
    for req in packet.buyer_data_requests:
        source=f" (`{req.source_type}`)" if req.source_type else ""
        lines.append(f"- **{req.timing} — {req.category}**{source}: {req.requirement}")
    lines.extend(["","## Buyer responsibilities",""])
    lines.extend(f"- {x}" for x in packet.buyer_responsibilities)
    lines.extend(["","## Freight Recovery responsibilities",""])
    lines.extend(f"- {x}" for x in packet.freight_responsibilities)
    lines.extend(["","## Blind-pilot sequence",""])
    lines.extend(f"- {x}" for x in packet.protocol_stages)
    lines.extend(["","## Buyer report separates",""])
    lines.extend(f"- {x}" for x in packet.buyer_report_totals)
    lines.extend(["","## Commercial integrity rules",""])
    lines.extend(f"- {x}" for x in packet.commercial_invariants)
    lines.extend(["","This packet is a deterministic activation/handoff artifact. It does not override the Pilot Launch Gate or prove a commercial outcome.",""])
    return "\n".join(lines)

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("readiness_input_json")
    parser.add_argument("launch_decision_json")
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    readiness_input=json.loads(Path(args.readiness_input_json).read_text(encoding="utf-8"))
    launch_decision=json.loads(Path(args.launch_decision_json).read_text(encoding="utf-8"))
    packet=build_packet(readiness_input,launch_decision)
    if args.format=="json":
        print(json.dumps(asdict(packet),indent=2))
    else:
        print(render_markdown(packet))

if __name__=="__main__":
    main()