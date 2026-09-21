#!/usr/bin/env python3
import hashlib, json, statistics, subprocess
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"dispatch_backpressure_policy.json").read_text(encoding="utf-8"))
DPOL=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8"))
EXEC_POL=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
PRIMARY=load_jsonl("dispatch_tickets.jsonl")
HISTORY=load_jsonl("dispatch_ticket_history.jsonl")
CLAIMS=load_jsonl("execution_claim_history.jsonl")
CANDIDATES=load_jsonl("routing_candidates.jsonl")
STATE=load_jsonl("execution_state.jsonl")
DMET=json.loads((INTEL/"dispatch_metrics.json").read_text(encoding="utf-8"))

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)

def fmt(dt):
    return None if dt is None else dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def git_clock():
    try:
        sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        raw=subprocess.check_output(["git","show","-s","--format=%cI","HEAD"],text=True).strip()
        return sha,parse_ts(raw)
    except Exception:
        return None,None

def ticket_id(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return "DISPATCH:"+hashlib.sha256(raw.encode()).hexdigest()[:12]

head_sha,now=git_clock()
claim_by_ticket={}
for c in CLAIMS:
    did=c.get("dispatch_ticket_id")
    if did and did not in claim_by_ticket:
        claim_by_ticket[did]=c

state_by_slot={x["slot_id"]:x for x in STATE}
active_workers={
    x.get("worker_id") for x in STATE
    if x.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"} and x.get("worker_id")
}
claimable=set(DPOL.get("ticket_valid_execution_states") or [])
history={x["dispatch_ticket_id"]:dict(x) for x in HISTORY if x.get("dispatch_ticket_id")}

rows=[]
for t in PRIMARY:
    issued=parse_ts(t.get("issued_at"))
    soft=parse_ts(t.get("soft_stale_at"))
    hard=parse_ts(t.get("hard_expire_at"))
    c=claim_by_ticket.get(t.get("dispatch_ticket_id"))
    latency=None
    if c and issued:
        ct=parse_ts(c.get("claimed_at"))
        if ct:
            latency=max(0,(ct-issued).total_seconds()/60.0)
    if c:
        lifecycle=c.get("status") or "CLAIMED"
    elif not issued or not soft or not hard or not now:
        lifecycle="LEGACY_UNTIMED"
    elif now>=hard:
        lifecycle="EXPIRED"
    elif now>=soft:
        lifecycle="STALE"
    else:
        lifecycle="PENDING"
    age=None if not issued or not now else max(0,(now-issued).total_seconds()/60.0)
    rows.append({
      "dispatch_ticket_id":t.get("dispatch_ticket_id"),
      "dispatch_generation_id":t.get("dispatch_generation_id"),
      "dispatch_kind":t.get("dispatch_kind") or "legacy_primary",
      "worker_id":t.get("worker_id"),
      "slot_id":t.get("slot_id"),
      "assignment_id":t.get("assignment_id"),
      "assignment_slot_role":t.get("assignment_slot_role"),
      "assignment_work_kind":t.get("assignment_work_kind"),
      "routing_score":t.get("routing_score"),
      "issued_at":t.get("issued_at"),
      "soft_stale_at":t.get("soft_stale_at"),
      "hard_expire_at":t.get("hard_expire_at"),
      "age_minutes":None if age is None else round(age,3),
      "lifecycle_state":lifecycle,
      "claim_id":None if not c else c.get("claim_id"),
      "claim_status":None if not c else c.get("status"),
      "claim_latency_minutes":None if latency is None else round(latency,3)
    })

agg=defaultdict(lambda:{"issued":0,"claimed":0,"expired":0,"stale":0,"latencies":[]})
for h in HISTORY:
    if h.get("dispatch_kind")!="primary" or not h.get("issued_at"):
        continue
    a=agg[h.get("worker_id")]
    a["issued"]+=1
    c=claim_by_ticket.get(h.get("dispatch_ticket_id"))
    if c:
        a["claimed"]+=1
        issued=parse_ts(h.get("issued_at"))
        ct=parse_ts(c.get("claimed_at"))
        if issued and ct:
            a["latencies"].append(max(0,(ct-issued).total_seconds()/60.0))
    elif now:
        hard=parse_ts(h.get("hard_expire_at"))
        soft=parse_ts(h.get("soft_stale_at"))
        if hard and now>=hard:
            a["expired"]+=1
        elif soft and now>=soft:
            a["stale"]+=1

min_events=int(POL.get("min_worker_dispatch_events_for_response_label",3))
min_latency=int(POL.get("min_claimed_events_for_latency_label",2))
workers=sorted({x.get("worker_id") for x in PRIMARY if x.get("worker_id")} | set(agg))
response=[]
for wid in workers:
    a=agg[wid]
    issued=a["issued"]
    claimed=a["claimed"]
    response.append({
      "worker_id":wid,
      "timed_primary_tickets":issued,
      "claimed_tickets":claimed,
      "claim_rate":None if not issued else round(claimed/issued,4),
      "stale_unclaimed":a["stale"],
      "expired_unclaimed":a["expired"],
      "median_claim_latency_minutes":None if len(a["latencies"])<min_latency else round(statistics.median(a["latencies"]),3),
      "evidence_state":"MEASURED" if issued>=min_events else ("SPARSE" if issued else "UNMEASURED")
    })

edges_by_slot=defaultdict(list)
for e in CANDIDATES:
    if e.get("slot_id"):
        edges_by_slot[e["slot_id"]].append(e)
for slot in edges_by_slot:
    edges_by_slot[slot].sort(key=lambda x:(-float(x.get("routing_score") or 0),x.get("worker_id") or ""))

backups=int(POL.get("work_steal_backups_per_expired_ticket",2))
ratio=float(POL.get("min_backup_score_ratio",0.75))
ttl=int(POL.get("work_steal_ticket_ttl_minutes",120))
steal=[]
claim_packets=[]

for bp in rows:
    if bp["lifecycle_state"]!="EXPIRED":
        continue
    parent=next((x for x in PRIMARY if x.get("dispatch_ticket_id")==bp["dispatch_ticket_id"]),None)
    if not parent:
        continue
    slot=parent.get("slot_id")
    s=state_by_slot.get(slot) or {}
    if s.get("status") not in claimable:
        continue
    pworker=parent.get("worker_id")
    pscore=float(parent.get("routing_score") or 0)
    eligible=[]
    for e in edges_by_slot.get(slot,[]):
        wid=e.get("worker_id")
        if not wid or wid==pworker or wid in active_workers:
            continue
        score=float(e.get("routing_score") or 0)
        if pscore>0 and score < pscore*ratio:
            continue
        eligible.append(e)
    for rank,e in enumerate(eligible[:backups],1):
        payload={
          "dispatch_kind":"work_steal",
          "parent_dispatch_ticket_id":parent["dispatch_ticket_id"],
          "worker_id":e["worker_id"],
          "routing_generation_id":parent["routing_generation_id"],
          "worker_profile_generation_id":parent["worker_profile_generation_id"],
          "routing_learning_generation_id":parent.get("routing_learning_generation_id"),
          "routing_exploration_generation_id":parent.get("routing_exploration_generation_id"),
          "routing_exploration_pair_id":parent.get("routing_exploration_pair_id"),
          "baseline_slot_id":parent.get("baseline_slot_id"),
          "route_mode":parent.get("route_mode"),
          "slot_id":parent["slot_id"],
          "assignment_id":parent["assignment_id"],
          "allocator_generation_id":parent["allocator_generation_id"],
          "portfolio_policy_generation_id":parent["portfolio_policy_generation_id"],
          "work_item_id":parent["work_item_id"],
          "assignment_slot_role":parent["assignment_slot_role"],
          "assignment_work_kind":parent["assignment_work_kind"],
          "assignment_source_id":parent["assignment_source_id"],
          "assignment_score":parent["assignment_score"],
          "routing_score":e.get("routing_score"),
          "steal_rank":rank
        }
        did=ticket_id(payload)
        old=history.get(did)
        if old:
            issued_at=old.get("issued_at")
            hard_expire_at=old.get("hard_expire_at")
            issued_commit_sha=old.get("issued_commit_sha")
        elif now:
            issued_at=fmt(now)
            hard_expire_at=fmt(now+timedelta(minutes=ttl))
            issued_commit_sha=head_sha
        else:
            issued_at=hard_expire_at=issued_commit_sha=None
        t={
          **payload,
          "dispatch_ticket_id":did,
          "ticket_schema_version":19,
          "dispatch_generation_id":parent.get("dispatch_generation_id"),
          "claim_file":parent.get("claim_file"),
          "eligible_at":parent.get("hard_expire_at"),
          "issued_at":issued_at,
          "soft_stale_at":None,
          "hard_expire_at":hard_expire_at,
          "issued_commit_sha":issued_commit_sha,
          "ticket_status":"STANDBY_WORK_STEAL"
        }
        if not old:
            history[did]={**t,"ticket_status":"ISSUED_WORK_STEAL"}
        steal.append(t)
        claim_packets.append({
          **t,
          "claim_schema_version":19,
          "routing_mode":"generated",
          "lease_minutes":int(EXEC_POL.get("default_lease_minutes",120))
        })

def write_jsonl(name,data):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in data)+("\n" if data else ""),encoding="utf-8")

steal.sort(key=lambda x:(x["slot_id"],x["steal_rank"],x["worker_id"]))
claim_packets.sort(key=lambda x:(x["slot_id"],x["steal_rank"],x["worker_id"]))
history_rows=sorted(history.values(),key=lambda x:x["dispatch_ticket_id"])
write_jsonl("dispatch_backpressure.jsonl",rows)
write_jsonl("worker_dispatch_response_metrics.jsonl",response)
write_jsonl("work_steal_tickets.jsonl",steal)
write_jsonl("work_steal_claim_packets.jsonl",claim_packets)
write_jsonl("dispatch_ticket_history.jsonl",history_rows)

DMET["history_tickets"]=len(history_rows)
DMET["current_work_steal_tickets"]=len(steal)
(INTEL/"dispatch_metrics.json").write_text(json.dumps(DMET,indent=2)+"\n",encoding="utf-8")

metrics={
  "schema_version":1,
  "clock_commit_sha":head_sha,
  "clock_timestamp":fmt(now),
  "primary_tickets":len(rows),
  "pending_primary":sum(1 for x in rows if x["lifecycle_state"]=="PENDING"),
  "stale_primary":sum(1 for x in rows if x["lifecycle_state"]=="STALE"),
  "expired_primary":sum(1 for x in rows if x["lifecycle_state"]=="EXPIRED"),
  "claimed_primary":sum(1 for x in rows if x["claim_id"]),
  "legacy_untimed_primary":sum(1 for x in rows if x["lifecycle_state"]=="LEGACY_UNTIMED"),
  "work_steal_tickets":len(steal),
  "measured_worker_response_profiles":sum(1 for x in response if x["evidence_state"]=="MEASURED")
}
(INTEL/"dispatch_backpressure_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# DISPATCH BACKPRESSURE REPORT","",
f"Clock: **{metrics['clock_timestamp'] or 'UNAVAILABLE'}**","",
f"- Primary tickets: **{metrics['primary_tickets']}**",
f"- Pending: **{metrics['pending_primary']}**",
f"- Stale: **{metrics['stale_primary']}**",
f"- Expired/unclaimed: **{metrics['expired_primary']}**",
f"- Claimed: **{metrics['claimed_primary']}**",
f"- Work-steal tickets: **{metrics['work_steal_tickets']}**","",
"| Worker | Slot | State | Age min | Claim latency min |",
"|---|---|---|---:|---:|"]
for x in rows:
    age="—" if x["age_minutes"] is None else f"{x['age_minutes']:.1f}"
    lat="—" if x["claim_latency_minutes"] is None else f"{x['claim_latency_minutes']:.1f}"
    report.append(f"| {x['worker_id']} | {x['slot_id']} | {x['lifecycle_state']} | {age} | {lat} |")
report += ["","Legacy untimed tickets are excluded from SLA judgments.",""]
(INTEL/"DISPATCH_BACKPRESSURE.md").write_text("\n".join(report),encoding="utf-8")

q=["# WORK STEAL QUEUE","",
"Standby work-steal tickets appear only after the primary ticket hard-expires. They do not auto-claim work.","",
"| Rank | Backup worker | Slot | Parent | Steal ticket | Score | Expires |",
"|---:|---|---|---|---|---:|---|"]
for x in steal:
    q.append(f"| {x['steal_rank']} | {x['worker_id']} | {x['slot_id']} | {x['parent_dispatch_ticket_id']} | {x['dispatch_ticket_id']} | {float(x['routing_score'] or 0):.3f} | {x.get('hard_expire_at') or '—'} |")
if not steal:
    q.append("| — | — | — | — | — | — | — |")
q += ["","V11 slot/worker concurrency and V15 ticket-time validation still apply.",""]
(INTEL/"WORK_STEAL_QUEUE.md").write_text("\n".join(q),encoding="utf-8")
print(json.dumps(metrics))
