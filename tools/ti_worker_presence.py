#!/usr/bin/env python3
import hashlib, json, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"worker_presence_policy.json").read_text(encoding="utf-8"))
REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
STATE=load_jsonl("execution_state.jsonl")
EVENT_DIR=INTEL/"worker_presence_events"

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

def fmt(dt):
    return None if dt is None else dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def git_clock():
    try:
        sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        raw=subprocess.check_output(["git","show","-s","--format=%cI","HEAD"],text=True).strip()
        return sha,parse_ts(raw)
    except Exception:
        return None,None

def read_events():
    rows=[]
    if not EVENT_DIR.exists():
        return rows
    for path in sorted(EVENT_DIR.glob("HUNTER-*.jsonl")):
        for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            try: obj=json.loads(line)
            except Exception as e: raise SystemExit(f"{path}:{n}: invalid JSON: {e}")
            obj["_path"]=str(path.relative_to(INTEL.parent))
            obj["_line"]=n
            rows.append(obj)
    return rows

head_sha,now=git_clock()
workers={x["worker_id"]:x for x in REG.get("workers",[])}
active={}
for s in STATE:
    if s.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"} and s.get("worker_id"):
        active[s["worker_id"]]=s

events=read_events()
by_worker={w:[] for w in workers}
seen=set()
errors=[]
allowed=set(POL.get("event_types") or [])
max_ttl=int(POL.get("max_ttl_minutes",180))
for e in events:
    eid=e.get("event_id"); wid=e.get("worker_id"); et=e.get("event_type")
    loc=f"{e.get('_path')}:{e.get('_line')}"
    if not eid or not str(eid).startswith("PRESENCE:") or eid in seen:
        errors.append(f"{loc}: invalid/duplicate event_id {eid}")
    else: seen.add(eid)
    if wid not in workers:
        errors.append(f"{loc}: unknown worker {wid}")
        continue
    expected=Path(e.get("_path","")).stem
    if expected!=wid:
        errors.append(f"{loc}: worker_id {wid} does not match file {expected}")
    if et not in allowed:
        errors.append(f"{loc}: invalid event_type {et}")
    ts=parse_ts(e.get("timestamp"))
    if not ts: errors.append(f"{loc}: invalid timestamp")
    ttl=e.get("ttl_minutes")
    if ttl is not None and (int(ttl)<1 or int(ttl)>max_ttl):
        errors.append(f"{loc}: ttl_minutes must be 1..{max_ttl}")
    by_worker[wid].append(e)

if errors: raise SystemExit("\n".join(errors))

rows=[]
history=[]
for wid in sorted(workers):
    evs=sorted(by_worker.get(wid,[]),key=lambda x:(parse_ts(x.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),x.get("event_id") or ""))
    for a,b in zip(evs,evs[1:]):
        if parse_ts(b.get("timestamp"))<parse_ts(a.get("timestamp")):
            raise SystemExit(f"{wid}: presence timestamps are not monotonic")
    latest=evs[-1] if evs else None
    state="UNKNOWN"; expires=None
    if wid in active:
        state="ACTIVE_CLAIM"
    elif latest:
        et=latest.get("event_type"); ts=parse_ts(latest.get("timestamp"))
        if et in {"READY","HEARTBEAT"}:
            default=int(POL.get("ready_ttl_minutes" if et=="READY" else "heartbeat_ttl_minutes",70))
            ttl=int(latest.get("ttl_minutes") or default)
            expires=ts+timedelta(minutes=ttl)
            state="READY_FRESH" if now and now<=expires else "READY_STALE"
        elif et=="BUSY": state="BUSY_DECLARED"
        elif et=="PAUSE": state="PAUSED"
        elif et=="OFFLINE": state="OFFLINE"
    rows.append({
      "worker_id":wid,
      "presence_state":state,
      "latest_event_id":None if not latest else latest.get("event_id"),
      "latest_event_type":None if not latest else latest.get("event_type"),
      "latest_event_at":None if not latest else latest.get("timestamp"),
      "presence_expires_at":fmt(expires),
      "active_claim_id":None if wid not in active else active[wid].get("claim_id"),
      "active_slot_id":None if wid not in active else active[wid].get("slot_id"),
      "event_count":len(evs)
    })
    for e in evs:
        history.append({k:v for k,v in e.items() if not k.startswith("_")})

fingerprint=json.dumps({
  "head_sha":head_sha,
  "now":fmt(now),
  "rows":[(x["worker_id"],x["presence_state"],x["latest_event_id"],x["presence_expires_at"],x["active_claim_id"]) for x in rows]
},sort_keys=True)
gen="PRESENCEGEN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in rows: x["presence_generation_id"]=gen

def write_jsonl(name,data):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in data)+("\n" if data else ""),encoding="utf-8")

write_jsonl("worker_presence_state.jsonl",rows)
write_jsonl("worker_presence_history.jsonl",history)

counts={}
for x in rows: counts[x["presence_state"]]=counts.get(x["presence_state"],0)+1
metrics={
  "schema_version":1,
  "presence_generation_id":gen,
  "clock_commit_sha":head_sha,
  "clock_timestamp":fmt(now),
  "registered_workers":len(rows),
  "state_counts":counts,
  "fresh_ready_workers":counts.get("READY_FRESH",0),
  "unknown_workers":counts.get("UNKNOWN",0),
  "presence_event_count":len(history)
}
(INTEL/"worker_presence_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# WORKER PRESENCE","",f"Generation: **{gen}**",f"Clock: **{fmt(now)}**","",
        "Presence is capacity telemetry, not a worker-quality score.","",
        "| Worker | State | Latest event | Expires | Active claim |","|---|---|---|---|---|"]
for x in rows:
    report.append(f"| {x['worker_id']} | **{x['presence_state']}** | {x.get('latest_event_id') or '—'} | {x.get('presence_expires_at') or '—'} | {x.get('active_claim_id') or '—'} |")
report += ["","Workers with UNKNOWN/STALE/OFFLINE/PAUSED presence do not receive V16 generated activation packets.",""]
(INTEL/"WORKER_PRESENCE.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
