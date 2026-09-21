#!/usr/bin/env python3
import json, re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ti_common import INTEL, load_jsonl

EVENT_DIR=INTEL/"execution_events"

def parse_ts(value):
    if not isinstance(value,str) or not value:
        raise ValueError("timestamp missing")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)

def fmt_ts(dt):
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def read_events():
    rows=[]
    if not EVENT_DIR.exists():
        return rows
    for path in sorted(EVENT_DIR.glob("SLOT-*.jsonl")):
        for line_no,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip():
                continue
            try:
                obj=json.loads(line)
            except Exception as e:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {e}")
            obj["_path"]=str(path.relative_to(INTEL.parent))
            obj["_line"]=line_no
            rows.append(obj)
    return rows

def build_execution_state(write=True, now=None):
    now=now or datetime.now(timezone.utc)
    policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
    dispatch_policy=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8")) if (INTEL/"dispatch_policy.json").exists() else {}
    dispatch_history=load_jsonl("dispatch_ticket_history.jsonl") if (INTEL/"dispatch_ticket_history.jsonl").exists() else []
    dispatch_by_id={x.get("dispatch_ticket_id"):x for x in dispatch_history if x.get("dispatch_ticket_id")}
    activation_policy=json.loads((INTEL/"activation_policy.json").read_text(encoding="utf-8")) if (INTEL/"activation_policy.json").exists() else {}
    activation_history=load_jsonl("activation_history.jsonl") if (INTEL/"activation_history.jsonl").exists() else []
    activation_by_id={x.get("activation_id"):x for x in activation_history if x.get("activation_id")}
    min_v16_claim_schema=int(activation_policy.get("minimum_claim_schema_version",16))
    legacy_claim_ids=set(dispatch_policy.get("legacy_claim_ids") or [])
    min_claim_schema=int(dispatch_policy.get("minimum_claim_schema_version",14))
    min_v15_claim_schema=int(dispatch_policy.get("minimum_v15_claim_schema_version",15))
    allocations=load_jsonl("hunt_allocations.jsonl")
    runs=load_jsonl("search_runs.jsonl")
    run_by_id={r.get("search_run_id"):r for r in runs if r.get("search_run_id")}
    alloc_by_slot={a["slot_id"]:a for a in allocations}
    events=read_events()
    events_by_slot=defaultdict(list)
    errors=[]
    event_ids=set()
    claim_ids_seen=set()

    for e in events:
        eid=e.get("event_id")
        if not eid or not re.match(r"^EXEC:[a-f0-9]{12}$",str(eid)):
            errors.append(f"{e.get('_path')}:{e.get('_line')}: invalid event_id {eid}")
        elif eid in event_ids:
            errors.append(f"{e.get('_path')}:{e.get('_line')}: duplicate event_id {eid}")
        else:
            event_ids.add(eid)
        slot=e.get("slot_id")
        expected=Path(e.get("_path","")).stem
        if not slot or slot!=expected:
            errors.append(f"{e.get('_path')}:{e.get('_line')}: slot_id {slot} does not match file {expected}")
        events_by_slot[slot].append(e)

    claim_history=[]
    state_rows=[]
    intervals=[]
    completed_events=[]

    max_lease=int(policy.get("max_lease_minutes",360))
    default_lease=int(policy.get("default_lease_minutes",120))
    heartbeat_default=int(policy.get("heartbeat_extension_minutes",120))
    allowed_types=set(policy.get("event_types") or [])

    for slot in sorted(alloc_by_slot):
        current=alloc_by_slot[slot]
        evs=events_by_slot.get(slot,[])
        last_ts=None
        active=None
        last_status="AVAILABLE"
        completed_assignments=set()
        terminal_failed_assignments=set()
        last_run_id=None
        last_claim=None
        last_worker=None
        last_expiry=None

        def close_active(status,end_ts,search_run_id=None,failure_code=None,retryable=None):
            nonlocal active,last_claim,last_worker,last_expiry,last_run_id,last_status
            if not active:
                return
            active["status"]=status
            active["ended_at"]=fmt_ts(end_ts)
            active["search_run_id"]=search_run_id
            active["failure_code"]=failure_code
            active["retryable"]=retryable
            intervals.append({
              "claim_id":active["claim_id"],
              "worker_id":active["worker_id"],
              "assignment_id":active["assignment_id"],
              "slot_id":slot,
              "start":active["_started_dt"],
              "end":end_ts
            })
            last_claim=active["claim_id"]
            last_worker=active["worker_id"]
            last_expiry=active.get("lease_expires_at")
            last_run_id=search_run_id or last_run_id
            last_status=status
            active=None

        for e in evs:
            loc=f"{e.get('_path')}:{e.get('_line')}"
            et=e.get("event_type")
            if et not in allowed_types:
                errors.append(f"{loc}: unknown event_type {et}")
                continue
            try:
                ts=parse_ts(e.get("timestamp"))
            except Exception as ex:
                errors.append(f"{loc}: {ex}")
                continue
            if last_ts is not None and ts<last_ts:
                errors.append(f"{loc}: timestamps must be append-monotonic")
            last_ts=ts

            # Time expiry is authoritative. A later event cannot revive an expired claim.
            if active and ts>active["_expiry_dt"]:
                close_active("EXPIRED",active["_expiry_dt"])
                last_status="EXPIRED_AVAILABLE"

            if et=="CLAIM":
                if active:
                    errors.append(f"{loc}: slot already has active claim {active['claim_id']}")
                    continue
                required=["claim_id","worker_id","assignment_id","allocator_generation_id",
                          "portfolio_policy_generation_id","work_item_id","assignment_slot_role",
                          "assignment_work_kind","assignment_source_id","assignment_score"]
                missing=[k for k in required if e.get(k) in {None,""}]
                if missing:
                    errors.append(f"{loc}: CLAIM missing {','.join(missing)}")
                    continue
                cid=e.get("claim_id")
                if not re.match(r"^CLAIM:[a-f0-9]{12}$",str(cid)):
                    errors.append(f"{loc}: invalid claim_id {cid}")
                    continue
                if cid in claim_ids_seen:
                    errors.append(f"{loc}: duplicate claim_id {cid}")
                    continue
                claim_ids_seen.add(cid)
                claim_schema=int(e.get("claim_schema_version") or 0)
                is_legacy_claim=cid in legacy_claim_ids and claim_schema<min_claim_schema
                if not is_legacy_claim:
                    if activation_policy and claim_schema<min_v16_claim_schema:
                        errors.append(f"{loc}: new CLAIM requires claim_schema_version >= {min_v16_claim_schema}")
                        continue
                    if claim_schema<min_claim_schema:
                        errors.append(f"{loc}: new CLAIM requires claim_schema_version >= {min_claim_schema}")
                        continue
                    mode=e.get("routing_mode")
                    if mode=="generated":
                        did=e.get("dispatch_ticket_id")
                        ticket=dispatch_by_id.get(did)
                        if not ticket:
                            errors.append(f"{loc}: generated CLAIM missing historical dispatch ticket {did}")
                            continue
                        ticket_schema=int(ticket.get("ticket_schema_version") or 0)
                        if ticket_schema>=15 and claim_schema<min_v15_claim_schema:
                            errors.append(f"{loc}: V15 dispatch ticket requires claim_schema_version >= {min_v15_claim_schema}")
                            continue
                        expected_ticket={
                          "worker_id":e.get("worker_id"),
                          "slot_id":slot,
                          "assignment_id":e.get("assignment_id"),
                          "allocator_generation_id":e.get("allocator_generation_id"),
                          "portfolio_policy_generation_id":e.get("portfolio_policy_generation_id"),
                          "work_item_id":e.get("work_item_id"),
                          "assignment_slot_role":e.get("assignment_slot_role"),
                          "assignment_work_kind":e.get("assignment_work_kind"),
                          "assignment_source_id":e.get("assignment_source_id"),
                          "routing_generation_id":e.get("routing_generation_id"),
                          "worker_profile_generation_id":e.get("worker_profile_generation_id"),
                          "routing_learning_generation_id":e.get("routing_learning_generation_id"),
                          "dispatch_generation_id":e.get("dispatch_generation_id")
                        }
                        if ticket_schema>=15:
                            expected_ticket["dispatch_kind"]=e.get("dispatch_kind")
                            expected_ticket["parent_dispatch_ticket_id"]=e.get("parent_dispatch_ticket_id")
                        drift=[k for k,v in expected_ticket.items() if ticket.get(k)!=v]
                        try:
                            if abs(float(ticket.get("assignment_score"))-float(e.get("assignment_score")))>1e-9:
                                drift.append("assignment_score")
                            if abs(float(ticket.get("routing_score"))-float(e.get("routing_score")))>1e-9:
                                drift.append("routing_score")
                        except Exception:
                            drift.append("score_parse")
                        if drift:
                            errors.append(f"{loc}: generated CLAIM dispatch binding mismatch: {','.join(sorted(set(drift)))}")
                            continue
                        if ticket_schema>=15:
                            eligible_raw=ticket.get("eligible_at") or ticket.get("issued_at")
                            hard_raw=ticket.get("hard_expire_at")
                            eligible=parse_ts(eligible_raw) if eligible_raw else None
                            hard=parse_ts(hard_raw) if hard_raw else None
                            if eligible and ts<eligible:
                                errors.append(f"{loc}: generated CLAIM before dispatch eligibility")
                                continue
                            if hard and ts>hard:
                                errors.append(f"{loc}: generated CLAIM after dispatch hard expiry")
                                continue
                        if activation_policy and claim_schema>=min_v16_claim_schema:
                            aid=e.get("activation_id")
                            act=activation_by_id.get(aid)
                            if not act:
                                errors.append(f"{loc}: generated CLAIM missing V16 activation {aid}")
                                continue
                            expected_activation={
                              "worker_id":e.get("worker_id"),
                              "slot_id":slot,
                              "dispatch_ticket_id":e.get("dispatch_ticket_id"),
                              "dispatch_generation_id":e.get("dispatch_generation_id"),
                              "presence_generation_id":e.get("presence_generation_id"),
                              "presence_event_id":e.get("presence_event_id"),
                              "activation_generation_id":e.get("activation_generation_id")
                            }
                            adrift=[k for k,v in expected_activation.items() if act.get(k)!=v]
                            if adrift:
                                errors.append(f"{loc}: V16 activation binding mismatch: {','.join(adrift)}")
                                continue
                            aexp=parse_ts(act.get("expires_at")) if act.get("expires_at") else None
                            if aexp and ts>aexp:
                                errors.append(f"{loc}: generated CLAIM after V16 activation expiry")
                                continue
                    elif mode=="manual_override":
                        if not str(e.get("route_override_reason") or "").strip():
                            errors.append(f"{loc}: manual_override CLAIM requires route_override_reason")
                            continue
                    else:
                        errors.append(f"{loc}: CLAIM requires routing_mode generated or manual_override")
                        continue
                assignment_id=e["assignment_id"]
                if assignment_id in completed_assignments:
                    errors.append(f"{loc}: assignment already completed in this slot log")
                    continue
                if assignment_id in terminal_failed_assignments:
                    errors.append(f"{loc}: non-retryable failed assignment cannot be reclaimed")
                    continue
                lease=int(e.get("lease_minutes") or default_lease)
                if lease<1 or lease>max_lease:
                    errors.append(f"{loc}: lease_minutes must be 1..{max_lease}")
                    continue
                expiry=ts+timedelta(minutes=lease)
                active={
                  "claim_id":cid,
                  "slot_id":slot,
                  "worker_id":e["worker_id"],
                  "assignment_id":assignment_id,
                  "allocator_generation_id":e["allocator_generation_id"],
                  "portfolio_policy_generation_id":e["portfolio_policy_generation_id"],
                  "work_item_id":e["work_item_id"],
                  "assignment_slot_role":e["assignment_slot_role"],
                  "assignment_work_kind":e["assignment_work_kind"],
                  "assignment_source_id":e["assignment_source_id"],
                  "assignment_score":e["assignment_score"],
                  "claim_schema_version":claim_schema if claim_schema else None,
                  "routing_mode":e.get("routing_mode"),
                  "routing_generation_id":e.get("routing_generation_id"),
                  "worker_profile_generation_id":e.get("worker_profile_generation_id"),
                  "routing_learning_generation_id":e.get("routing_learning_generation_id"),
                  "routing_score":e.get("routing_score"),
                  "dispatch_ticket_id":e.get("dispatch_ticket_id"),
                  "dispatch_generation_id":e.get("dispatch_generation_id"),
                  "dispatch_kind":e.get("dispatch_kind"),
                  "parent_dispatch_ticket_id":e.get("parent_dispatch_ticket_id"),
                  "presence_generation_id":e.get("presence_generation_id"),
                  "presence_event_id":e.get("presence_event_id"),
                  "activation_id":e.get("activation_id"),
                  "activation_generation_id":e.get("activation_generation_id"),
                  "route_override_reason":e.get("route_override_reason"),
                  "claimed_at":fmt_ts(ts),
                  "lease_expires_at":fmt_ts(expiry),
                  "last_heartbeat_at":None,
                  "started_at":None,
                  "ended_at":None,
                  "status":"CLAIMED",
                  "search_run_id":None,
                  "failure_code":None,
                  "retryable":None,
                  "_started_dt":ts,
                  "_expiry_dt":expiry
                }
                claim_history.append(active)
                last_claim=cid
                last_worker=e["worker_id"]
                last_expiry=fmt_ts(expiry)
                last_status="CLAIMED"
                continue

            cid=e.get("claim_id")
            if not active:
                errors.append(f"{loc}: {et} has no live claim (possibly expired/released)")
                continue
            if cid!=active["claim_id"]:
                errors.append(f"{loc}: claim_id {cid} does not match active {active['claim_id']}")
                continue
            if e.get("worker_id") not in {None,active["worker_id"]}:
                errors.append(f"{loc}: worker_id does not match claim owner")
                continue

            if et=="HEARTBEAT":
                ext=int(e.get("extend_minutes") or heartbeat_default)
                if ext<1 or ext>max_lease:
                    errors.append(f"{loc}: extend_minutes must be 1..{max_lease}")
                    continue
                expiry=ts+timedelta(minutes=ext)
                active["_expiry_dt"]=expiry
                active["lease_expires_at"]=fmt_ts(expiry)
                active["last_heartbeat_at"]=fmt_ts(ts)
                last_expiry=fmt_ts(expiry)
            elif et=="START":
                active["status"]="RUNNING"
                active["started_at"]=fmt_ts(ts)
                last_status="RUNNING"
            elif et=="COMPLETE":
                rid=e.get("search_run_id")
                if not rid:
                    errors.append(f"{loc}: COMPLETE requires search_run_id")
                    continue
                completed_assignments.add(active["assignment_id"])
                completed_events.append((dict(active),e))
                close_active("COMPLETE",ts,search_run_id=rid)
            elif et=="FAIL":
                retryable=bool(e.get("retryable"))
                code=e.get("failure_code") or "UNSPECIFIED"
                if not retryable:
                    terminal_failed_assignments.add(active["assignment_id"])
                    close_active("FAILED_TERMINAL",ts,failure_code=code,retryable=False)
                else:
                    close_active("FAILED_RETRYABLE",ts,failure_code=code,retryable=True)
                    last_status="RETRYABLE_AVAILABLE"
            elif et=="RELEASE":
                close_active("RELEASED",ts)
                last_status="RELEASED_AVAILABLE"

        # Expire live claim as of current control-plane evaluation.
        if active and now>active["_expiry_dt"]:
            close_active("EXPIRED",active["_expiry_dt"])
            last_status="EXPIRED_AVAILABLE"

        if active:
            intervals.append({
              "claim_id":active["claim_id"],
              "worker_id":active["worker_id"],
              "assignment_id":active["assignment_id"],
              "slot_id":slot,
              "start":active["_started_dt"],
              "end":active["_expiry_dt"],
              "provisional_live":True
            })

        current_id=current.get("assignment_id")
        current_completed=current_id in completed_assignments
        current_failed=current_id in terminal_failed_assignments

        if active:
            superseded=active["assignment_id"]!=current_id
            if active["status"]=="RUNNING":
                final_status="RUNNING_SUPERSEDED" if superseded else "RUNNING"
            else:
                final_status="CLAIMED_SUPERSEDED" if superseded else "CLAIMED"
            telemetry="PENDING"
            claim_id=active["claim_id"]
            worker=active["worker_id"]
            claimed_assignment=active["assignment_id"]
            lease_exp=active["lease_expires_at"]
            run_id=None
        else:
            if current_completed:
                final_status="COMPLETE"
                telemetry="PENDING"
            elif current_failed:
                final_status="FAILED_TERMINAL"
                telemetry="NOT_APPLICABLE"
            elif last_status in {"EXPIRED_AVAILABLE","RETRYABLE_AVAILABLE","RELEASED_AVAILABLE"}:
                final_status=last_status
                telemetry="NOT_APPLICABLE"
            else:
                final_status="AVAILABLE"
                telemetry="NOT_APPLICABLE"
            claim_id=last_claim if current_completed else None
            worker=last_worker if current_completed else None
            claimed_assignment=current_id if current_completed else None
            lease_exp=last_expiry if current_completed else None
            run_id=last_run_id if current_completed else None

        state_rows.append({
          "slot_id":slot,
          "current_assignment_id":current_id,
          "current_work_item_id":current.get("work_item_id"),
          "current_slot_role":current.get("slot_role"),
          "current_work_kind":current.get("work_kind"),
          "status":final_status,
          "claim_id":claim_id,
          "worker_id":worker,
          "claimed_assignment_id":claimed_assignment,
          "lease_expires_at":lease_exp,
          "search_run_id":run_id,
          "telemetry_status":telemetry,
          "event_count":len(evs)
        })

    # Any event file not represented by a current slot is malformed.
    for slot in events_by_slot:
        if slot not in alloc_by_slot:
            errors.append(f"execution event log exists for unknown slot {slot}")

    # Detect overlapping claims by worker and by exact assignment.
    def overlap_check(key_name):
        groups=defaultdict(list)
        for x in intervals:
            groups[x[key_name]].append(x)
        for key,items in groups.items():
            if not key:
                continue
            items=sorted(items,key=lambda x:x["start"])
            for prev,cur in zip(items,items[1:]):
                if cur["start"]<prev["end"]:
                    errors.append(
                      f"overlapping active claims for {key_name}={key}: "
                      f"{prev['claim_id']} ({prev['slot_id']}) and {cur['claim_id']} ({cur['slot_id']})"
                    )
    overlap_check("worker_id")
    overlap_check("assignment_id")

    # Enforce completion -> telemetry handoff and update history/state telemetry status.
    history_by_claim={x["claim_id"]:x for x in claim_history}
    completion_by_claim={}
    for claim,event in completed_events:
        cid=claim["claim_id"]
        rid=event.get("search_run_id")
        run=run_by_id.get(rid)
        telemetry="MATCHED"
        if not run:
            telemetry="MISSING"
            errors.append(f"COMPLETE claim {cid}: search_run_id {rid} not found")
        else:
            expected={
              "execution_claim_id":cid,
              "execution_slot_id":claim["slot_id"],
              "execution_worker_id":claim["worker_id"],
              "assignment_id":claim["assignment_id"],
              "allocator_generation_id":claim["allocator_generation_id"],
              "portfolio_policy_generation_id":claim["portfolio_policy_generation_id"],
              "assignment_work_item_id":claim["work_item_id"],
              "assignment_slot_role":claim["assignment_slot_role"],
              "assignment_work_kind":claim["assignment_work_kind"],
              "assignment_source_id":claim["assignment_source_id"]
            }
            if claim.get("routing_generation_id"):
                expected["routing_generation_id"]=claim.get("routing_generation_id")
                expected["worker_profile_generation_id"]=claim.get("worker_profile_generation_id")
            if int(claim.get("claim_schema_version") or 0)>=14:
                expected["routing_mode"]=claim.get("routing_mode")
                if claim.get("routing_mode")=="generated":
                    expected["routing_learning_generation_id"]=claim.get("routing_learning_generation_id")
                    expected["dispatch_ticket_id"]=claim.get("dispatch_ticket_id")
                    expected["dispatch_generation_id"]=claim.get("dispatch_generation_id")
                    if int(claim.get("claim_schema_version") or 0)>=15:
                        expected["dispatch_kind"]=claim.get("dispatch_kind")
                        expected["parent_dispatch_ticket_id"]=claim.get("parent_dispatch_ticket_id")
                elif claim.get("routing_mode")=="manual_override":
                    expected["route_override_reason"]=claim.get("route_override_reason")
            mismatches=[f"{k}:run={run.get(k)!r}:claim={v!r}" for k,v in expected.items() if run.get(k)!=v]
            if int(run.get("schema_version") or 0)<11:
                mismatches.append(f"schema_version={run.get('schema_version')} < 11")
            try:
                score_match=abs(float(run.get("assignment_score"))-float(claim["assignment_score"]))<1e-9
            except Exception:
                score_match=False
            if not score_match:
                mismatches.append("assignment_score mismatch")
            if claim.get("routing_generation_id"):
                try:
                    route_score_match=abs(float(run.get("routing_score"))-float(claim.get("routing_score")))<1e-9
                except Exception:
                    route_score_match=False
                if not route_score_match:
                    mismatches.append("routing_score mismatch")
            if mismatches:
                telemetry="MISMATCH"
                errors.append(f"COMPLETE claim {cid}: telemetry mismatch: {'; '.join(mismatches)}")
        completion_by_claim[cid]=(rid,telemetry)
        h=history_by_claim.get(cid)
        if h:
            h["telemetry_status"]=telemetry
        for s in state_rows:
            if s["claim_id"]==cid and s["status"]=="COMPLETE":
                s["telemetry_status"]=telemetry
                s["search_run_id"]=rid

    # Materialize claim history without private datetime helpers.
    history_rows=[]
    for h in claim_history:
        out={k:v for k,v in h.items() if not k.startswith("_")}
        if "telemetry_status" not in out:
            out["telemetry_status"]="PENDING" if out.get("status") in {"CLAIMED","RUNNING"} else "NOT_APPLICABLE"
        history_rows.append(out)

    if errors:
        raise SystemExit("\n".join(errors))

    metrics={
      "schema_version":1,
      "slot_count":len(state_rows),
      "event_count":len(events),
      "claim_count":len(history_rows),
      "status_counts":{},
      "active_claims":0,
      "complete_claims":sum(1 for h in history_rows if h.get("status")=="COMPLETE"),
      "telemetry_matched_completions":sum(1 for h in history_rows if h.get("telemetry_status")=="MATCHED"),
      "telemetry_debt_completions":sum(1 for h in history_rows if h.get("status")=="COMPLETE" and h.get("telemetry_status")!="MATCHED")
    }
    for s in state_rows:
        metrics["status_counts"][s["status"]]=metrics["status_counts"].get(s["status"],0)+1
        if s["status"] in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}:
            metrics["active_claims"]+=1

    if write:
        def write_jsonl(name,rows):
            (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")
        write_jsonl("execution_state.jsonl",state_rows)
        write_jsonl("execution_claim_history.jsonl",history_rows)
        (INTEL/"execution_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

        board=[
          "# HUNT EXECUTION BOARD","",
          "V11 derives execution state from append-only per-slot events. Missing event logs mean AVAILABLE.","",
          "| Slot | Role | Assignment | State | Worker | Claim | Telemetry |",
          "|---|---|---|---|---|---|---|"
        ]
        for s in state_rows:
            board.append(
              f"| {s['slot_id']} | {s.get('current_slot_role') or '—'} | {s.get('current_assignment_id') or '—'} | "
              f"**{s['status']}** | {s.get('worker_id') or '—'} | {s.get('claim_id') or '—'} | {s['telemetry_status']} |"
            )
        board += ["","## Claim protocol","",
          "1. Claim by appending a CLAIM event to the slot's JSONL file using optimistic file-SHA concurrency.",
          "2. Heartbeat before lease expiry for long work.",
          "3. Write the V11 search-run telemetry before appending COMPLETE.",
          "4. COMPLETE only after the search run exists with exact claim and assignment provenance.",
          "5. Retryable FAIL or RELEASE returns the slot to the claimable pool; non-retryable FAIL blocks the same assignment.",
          ""]
        (INTEL/"EXECUTION_BOARD.md").write_text("\n".join(board),encoding="utf-8")

        debt=[
          "# EXECUTION DEBT","",
          "Operational debt is distinct from research/measurement debt.","",
          f"- Available/claimable slots: **{sum(1 for s in state_rows if s['status'] in {'AVAILABLE','EXPIRED_AVAILABLE','RETRYABLE_AVAILABLE','RELEASED_AVAILABLE'})}**",
          f"- Active claims: **{metrics['active_claims']}**",
          f"- Completed with matched telemetry: **{metrics['telemetry_matched_completions']}**",
          f"- Completion telemetry debt: **{metrics['telemetry_debt_completions']}**","",
          "## Items requiring attention",""
        ]
        items=0
        for s in state_rows:
            if s["status"] in {"EXPIRED_AVAILABLE","RETRYABLE_AVAILABLE","FAILED_TERMINAL","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"} or s["telemetry_status"] in {"MISSING","MISMATCH"}:
                debt.append(f"- {s['slot_id']}: {s['status']} / telemetry={s['telemetry_status']} / assignment={s.get('current_assignment_id')}")
                items+=1
        if not items:
            debt.append("- None.")
        debt.append("")
        (INTEL/"EXECUTION_DEBT.md").write_text("\n".join(debt),encoding="utf-8")

    return state_rows,history_rows,metrics

if __name__=="__main__":
    states,claims,metrics=build_execution_state(write=True)
    print(json.dumps(metrics))
