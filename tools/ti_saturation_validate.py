#!/usr/bin/env python3
import json,re
from ti_common import INTEL, load_jsonl

rows=load_jsonl("research_neighborhoods.jsonl")
redirects=load_jsonl("redirect_queue.jsonl")
allowed_types={"capability","query_family","search_objective","adjacency_type","adjacency_root","search_seed"}
allowed_status={"INSUFFICIENT","PRODUCTIVE","BALANCED","SATURATING","SATURATED"}
allowed_action={"MEASURE_MORE","CONTINUE_BOUNDED","CONTINUE_WITH_DIVERSITY","DIVERSIFY_SURFACE_OR_ADJACENCY","SHIFT_TO_EXPERIMENT_OR_UNDEREXPLORED_NEIGHBORHOOD"}
seen=set()
for n,x in enumerate(rows,1):
    nid=x.get("neighborhood_id")
    if not nid or not re.match(r"^NBR:[a-z0-9-]+:.+",nid):
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: invalid neighborhood_id {nid}")
    if nid in seen:
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: duplicate neighborhood_id {nid}")
    seen.add(nid)
    if x.get("neighborhood_type") not in allowed_types:
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: invalid neighborhood_type")
    if x.get("status") not in allowed_status:
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: invalid status")
    if x.get("recommended_action") not in allowed_action:
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: invalid action")
    if x.get("status") in {"SATURATING","SATURATED","PRODUCTIVE","BALANCED"} and not x.get("sufficient_evidence"):
        raise SystemExit(f"research_neighborhoods.jsonl:{n}: non-insufficient status without sufficient evidence")
    if x.get("status")=="SATURATED":
        if x.get("runs",0)<5 or x.get("deep_inspected",0)<20 or x.get("trailing_no_delta_runs",0)<3:
            raise SystemExit(f"research_neighborhoods.jsonl:{n}: saturated without minimum evidence")
for n,x in enumerate(redirects,1):
    if x.get("neighborhood_id") not in seen:
        raise SystemExit(f"redirect_queue.jsonl:{n}: unknown neighborhood")
    if not 0<=x.get("priority",0)<=100:
        raise SystemExit(f"redirect_queue.jsonl:{n}: priority out of range")
metrics=json.loads((INTEL/"saturation_metrics.json").read_text(encoding="utf-8"))
if metrics.get("neighborhood_count")!=len(rows):
    raise SystemExit("saturation_metrics.json: neighborhood count drift")
print(f"OK neighborhoods={len(rows)} redirects={len(redirects)} saturated={metrics.get('saturated_neighborhoods',0)}")
