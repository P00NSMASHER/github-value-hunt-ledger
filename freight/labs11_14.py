"""Labs 11-14: deterministic, synthetic freight operating simulations.

Uses only fictional freight source invoices. No customer contact, provider
network calls, money movement, certification, or model-performance claims.
Full-case output is compact; the event log is regenerated deterministically
from the frozen source row for independent replay and verification.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone

LAB_NAMES={
 11:"PRODUCTION_RELIABILITY_DISASTER_RECOVERY",
 12:"FRAUD_EVIDENCE_INTEGRITY_FINANCIAL_CONTROLS",
 13:"CONTINUOUS_SAVINGS_COST_INTELLIGENCE",
 14:"COMPETITIVE_BENCHMARK_MARKET_EXPANSION",
}
MODES=("PARCEL","LTL","TL","INTERMODAL","AIR","OCEAN")
FAMILIES={
11:("HEALTHY","HTTP_503","SQL_LOCK","DUPLICATE_MESSAGE","TIMEOUT_AFTER_WRITE","REGION_FAILOVER",
"WORKER_CRASH","UNACKED_MESSAGE","READ_ONLY_RESTORE","QUEUE_REORDER","STORAGE_OUTAGE","BACKPRESSURE",
"POISON_PAYLOAD","INVALID_DIGEST","TENANT_MISMATCH","EXPIRED_AUTH","WORKER_OOM","RATE_LIMIT",
"NETWORK_PARTITION","STORAGE_QUOTA","TORN_CHECKPOINT","SQL_ROLLBACK","STALE_CACHE","CANARY_ROLLBACK",
"OVERSIZED_INPUT","MAINTENANCE_PAUSE","PARTIAL_BATCH","RETRY_REPLAY","DUPLICATE_OUTBOX","MISSING_SOURCE",
"INVALID_SCHEMA","NONMONOTONIC_TIME","SCHEMA_DRIFT","DEPENDENCY_TIMEOUT","RETRY_EXHAUSTION","RESTORE_INCOMPLETE"),
12:("CLEAN","FORGED_INVOICE","ALTERED_RATE","FAKE_CREDIT","FALSE_SETTLEMENT","BANK_CHANGE",
"CARRIER_IMPERSONATION","BUYER_IMPERSONATION","DUPLICATE_RECOVERY","PREEXISTING_CREDIT","UNAUTHORIZED_SETTLEMENT",
"PAYMENT_REPLAY","CROSS_TENANT_READ","CROSS_TENANT_WRITE","UNSIGNED_CONTRACT","REVOKED_CONSENT",
"FORGED_REVIEWER","MISSING_CHAIN","INVALID_BENEFICIARY","INVALID_PAYMENT_CURRENCY","MODIFIED_SOURCE",
"INSIDER_OVERRIDE","UNVERIFIED_BANK_DETAILS","FAKE_PO_NUMBER","CLAIM_DOUBLE_COUNT","CUSTOMER_DATA_LEAK",
"PHISHING_REPLY_TO","STALE_AUTHORIZATION","DISPUTED_INVOICE","CARRIER_REFUND_REVERSAL","SOCIAL_ENGINEERING",
"REMITTANCE_MISMATCH","HASH_RECOMPUTED","UNKNOWN_SOURCE","NEGATIVE_AUDIT","NO_CLAIM_RIGHTS"),
13:("LANE_CONSOLIDATION","CONTRACT_RENEGOTIATION","PACKAGING_DIMENSION","MODE_SWITCH","CARRIER_MIX",
"FUEL_CAP","LIFTGATE_AVOIDANCE","RESIDENTIAL_AVOIDANCE","POOL_DISTRIBUTION","MULTISTOP_TL",
"SERVICE_LEVEL","LOAD_CONSOLIDATION","INVOICE_PROCESSING","REDUCE_REDELIVERY","APPOINTMENT_WINDOW",
"VOLUME_REBATE","ZONE_OPTIMIZATION","ROUTE_DENSITY","CROSS_DOCK","RETURN_POOLING","SURCHARGE_PREVENTION",
"PICKUP_COORDINATION","PACKAGING_REDESIGN","VOLUMETRIC_WEIGHT","RATE_INDEX","SPOT_BUY",
"STORAGE_TIME","CARRIER_DIVERSIFICATION","LATE_BOOKING","DUPLICATE_ALTERNATIVE","NO_BID_EVIDENCE",
"SAFETY_SERVICE_CONSTRAINT","CAPACITY_LIMIT","CONTRACT_VETO","SEASONALITY_UNPROVEN","ZERO_BASELINE"),
14:("SECOND_LOOK","SOURCE_PROVENANCE","RATING_BREADTH","REAL_WORLD_ACCURACY","DOCUMENT_EXTRACTION",
"NAMED_TMS_ERP","DIRECT_PAYMENT_RAILS","ANALYTICS","INDEPENDENT_SECURITY","SSO_MFA","PRODUCTION_SLA",
"MULTICURRENCY","COST_ALLOCATION","CLAIM_AUTOMATION","SHADOW_AUDIT","RECONCILED_CASH","CUSTOMER_REFERENCE",
"SALES_IMPLEMENTATION","EXCEPTION_WORKFLOW","REVIEWER_EXPERTISE","CARRIER_INTEGRATION","FREIGHT_AP_ACCOUNTS",
"SETTLEMENT_REVERSAL","REST_API","SECURE_DOCUMENTS","CARRIER_SCORECARD","FUTURE_COST_SAVINGS",
"SKU_ALLOCATION","BLIND_AUDIT_BENCHMARK","GLOBAL_SUPPORT","PRICE_TRANSPARENCY","EVIDENCE_EXPORT",
"PROCUREMENT_READY","DISASTER_RECOVERY","INCREMENTAL_RECOVERY_PROOF","INTERNATIONAL_OPS")
}
VENDOR_SOURCES=(
 ("Intelligent Audit","https://www.intelligentaudit.com/products/farbi","VENDOR_PUBLIC_CLAIM"),
 ("Trax","https://www.traxtech.com/","VENDOR_PUBLIC_CLAIM"),
 ("Cass Information Systems","https://www.cassinfo.com/freight-audit-payment/services/freight-audit","VENDOR_PUBLIC_CLAIM"),
 ("Loop","https://www.loop.com/article/introducing-the-long-horizon-auditbench-for-supply-chain-ai","VENDOR_PUBLISHED_BENCHMARK"),
 ("nVision Global","https://corporate.nvisionglobal.com/campaigns/ai-driven-freight-audit-payment/","VENDOR_PUBLIC_CLAIM"),
)
KNOWN_INTERNAL={"SECOND_LOOK","SOURCE_PROVENANCE","RATING_BREADTH","ANALYTICS","SHADOW_AUDIT","SETTLEMENT_REVERSAL","EVIDENCE_EXPORT"}
RELIABILITY_PERMANENT={12,13,14,15,20,24,29,30,31,35}
RELIABILITY_EXHAUST={16,18,19,34}
FRAUD_HIGH_RISK=set(range(1,18))|{18,19,20,21,22,24,25,26,27,30,31,32,33,35}
SAVINGS_REVIEW={29,30,31,32,33,34,35}

def compact(value):
 return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def sha(obj):
 return hashlib.sha256(compact(obj)).hexdigest()

def pick(lab,index,seed,extra="scenario"):
 payload=f"fictional:{lab}:{index}:{seed}:{extra}".encode()
 return int.from_bytes(hashlib.blake2b(payload,digest_size=8).digest(),"big")

def prepare_source(row,index):
 if row["invoice_id"]!=f"INV-{index:07d}" or not row["customer_id"].startswith("CUSTOMER-"):
  raise ValueError("synthetic invoice population not frozen or reordered")
 if not row["carrier_id"].startswith("FICTIONAL-") or row["mode"] not in MODES:
  raise ValueError("nonfictional source or bad freight mode")
 digest=row["synthetic_source_sha256"]
 if len(digest)!=64 or any(ch not in "0123456789abcdef" for ch in digest):
  raise ValueError("invalid source fingerprint")
 return {"invoice_id":row["invoice_id"],"customer_id":row["customer_id"],
  "carrier_id":row["carrier_id"],"source_sha256":digest,"mode":row["mode"],
  "truth":row["truth_state"],"evidence_state":row["evidence_state"],
  "contract_id":row["contract_id"],"gross_cents":int(row["invoice_total_cents"]),
  "contract_base_cents":int(row["expected_base_cents"]),
  "contract_fuel_cents":int(row["expected_fuel_cents"]),
  "contract_accessorial_cents":int(row["expected_accessorial_cents"]),
  "eligible_cents":int(row["net_eligible_cents"])}
 
def simulate(lab,row,index,seed=20261007,include_events=False):
 """One event-replayable business scenario, independent of any real external system."""
 if lab not in LAB_NAMES:raise ValueError("unknown lab")
 src=prepare_source(row,index)
 variant=pick(lab,index,seed)%36
 kind=FAMILIES[lab][variant]
 scenario=f"LAB{lab:02d}-{index:07d}"
 cents={};flags={};steps=[]
 def add(code,money=0,note=""):
  if type(money)!=int or money<0:raise ValueError("invalid event cents")
  steps.append((code,money,str(note)[:90]))
 add("FICTITIOUS_SOURCE_FROZEN",0,src["source_sha256"][:16])
 if lab==11:
  quarantine=variant in RELIABILITY_PERMANENT
  deadletter=variant in RELIABILITY_EXHAUST
  tries=0 if quarantine else 4 if deadletter else (1 if variant==0 else 2+pick(lab,index,seed,"tries")%2)
  commit=0 if (quarantine or deadletter) else 1
  add("QUEUE_REQUEST",0,kind)
  if quarantine:add("ISOLATED_INVALID_INPUT",0,kind)
  else:
   for n in range(tries):
    add("DISPATCH_ATTEMPT",0,str(n+1))
   if deadletter:add("DEAD_LETTER",0,"bounded")
   else:add("COMMIT_IDEMPOTENT",0,"one-synthetic-write");add("ACK_AFTER_WRITE")
  flags={"fault":kind,"attempts":tries,"max_attempts":4,"write_count":commit,
   "acked":bool(commit),"isolated":quarantine,"dead_letter":deadletter,
   "duplicate_delivery_count":2+variant%3 if variant in (3,4,28) else 1,
   "model_latency_ms":tries*150+variant%50,"real_production_load_test":False}
  cents={"customer_cash_cents":0}
  decision="ACCEPT" if commit else "HOLD"
  outcome="IDEMPOTENT_COMMIT" if commit else "QUARANTINE" if quarantine else "DEAD_LETTER"
 elif lab==12:
  risk=variant in FRAUD_HIGH_RISK
  clean=variant==0 and src["truth"]=="POSITIVE" and src["evidence_state"]=="VERIFIED_SYNTHETIC"
  candidate=src["eligible_cents"] if clean else 0
  add("INDEPENDENT_THREAT_CLASSIFICATION",0,kind)
  add("IDENTITY_AND_PAYMENT_GATE",0,"HOLD" if risk else "REVIEW")
  add("NO_EXTERNAL_BANK_ACTION",0,"synthetic mode")
  if candidate:add("CANDIDATE_ONLY",candidate,"not cash")
  flags={"threat":kind,"fraud_ground_truth":risk,"independent_approver_required":risk,
   "real_penetration_test":False,"bank_action":False,"carrier_contact":False}
  cents={"candidate_cents":candidate,"settled_cents":0,"fee_collected_cents":0,"transferred_cents":0}
  decision="BLOCK" if risk else "REVIEW"
  outcome="FRAUD_HOLD" if risk else "EVIDENCE_ONLY"
 elif lab==13:
  base=src["contract_base_cents"]+src["contract_fuel_cents"]+src["contract_accessorial_cents"]
  bps=50+pick(lab,index,seed,"basis")%650
  gross=min(base,(base*bps+5000)//10000)
  implementation=(base*(45+pick(lab,index,seed,"cost")%180)+5000)//10000
  review=variant in SAVINGS_REVIEW or src["truth"]=="REVIEW" or not base
  hypothesis=max(0,gross-implementation) if not review else 0
  add("HISTORICAL_BASELINE",base,src["contract_id"])
  add("COUNTERFACTUAL_MODELED",gross,kind)
  add("IMPLEMENTATION_COST_MODELED",implementation,"assumption")
  add("BUYER_EXPERIMENT_REQUIRED",0,"not observed savings")
  flags={"tactic":kind,"bps_assumed":bps,"buyer_authorized":False,
   "actual_carrier_quote":False,"controlled_field_experiment":False,
   "manual_review_required":True}
  cents={"baseline_cents":base,"hypothetical_gross_cents":gross,
         "implementation_cost_cents":implementation,
         "hypothetical_net_cents":hypothesis,"actual_savings_cents":0,
         "realized_recovery_cents":0,"prior_overpayment_separate_cents":src["eligible_cents"]}
  decision="PROPOSE_TEST" if hypothesis>0 else "HOLD"
  outcome="COUNTERFACTUAL_HYPOTHESIS" if hypothesis>0 else "UNPROVEN"
 elif lab==14:
  vendor=VENDOR_SOURCES[pick(lab,index,seed,"vendor")%len(VENDOR_SOURCES)]
  internal=kind in KNOWN_INTERNAL
  add("BUYER_CAPABILITY_REQUIREMENT",0,kind)
  add("SOURCE_EVIDENCE_TYPE",0,vendor[2])
  add("NO_COMPETITOR_PERFORMANCE_TEST",0,"not measured")
  add("PURCHASER_VALIDATION_GATE",0,"external proof required")
  flags={"requirement":kind,"competitor":vendor[0],"competitor_url":vendor[1],
   "competitor_evidence":vendor[2],"recoveryos_internal_assertion":internal,
   "independent_competitor_test":False,"verified_competitor_win":False,
   "vendor_accuracy_measured_here":False,"real_customer_willingness_to_pay":False}
  cents={"competitor_observed_recovery_cents":0,"recoveryos_observed_revenue_cents":0}
  decision="REVIEW_EVIDENCE"
  outcome="PILOT_SCOPE_POSSIBLE" if internal else "EXTERNAL_PROOF_PENDING"
 prior="0"*64;events=[]
 for number,(code,money,note) in enumerate(steps,1):
  time=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=index%365,minutes=number*19)).isoformat(timespec="seconds").replace("+00:00","Z")
  ev={"scenario_id":scenario,"sequence":number,"time_utc":time,
   "code":code,"amount_cents":money,"note":note,"previous_sha256":prior}
  ev["sha256"]=sha(ev);prior=ev["sha256"]
  if include_events:events.append(ev)
 out={"lab":lab,"index":index,"scenario_id":scenario,
  "scenario_family":kind,"variant":variant,"invoice_id":src["invoice_id"],
  "customer_id":src["customer_id"],"carrier_id":src["carrier_id"],
  "source_sha256":src["source_sha256"],"mode":src["mode"],
  "truth":src["truth"],"evidence_state":src["evidence_state"],
  "source_eligible_cents":src["eligible_cents"],"decision":decision,
  "outcome":outcome,"checks":flags,"cents":cents,"event_count":len(steps),
  "event_head_sha256":prior,"evidence_class":"SIMULATED_ONLY"}
 out["case_sha256"]=sha(out)
 if include_events:out["events"]=events
 return out
