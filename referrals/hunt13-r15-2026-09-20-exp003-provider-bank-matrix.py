from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib, json, random, threading, time

class Authority(str, Enum): VERIFIED="VERIFIED"; REVIEW="REVIEW"
class Provider(str, Enum): NOT_SENT="NOT_SENT"; UNKNOWN="UNKNOWN"; DEFINITE_REFUSAL="DEFINITE_REFUSAL"; CONFIRMED="CONFIRMED"
class Coverage(str, Enum): VERIFIED_WINDOW="VERIFIED_WINDOW"; STALE="STALE"; INITIALIZING="INITIALIZING"; PARTIAL="PARTIAL"; UNAVAILABLE="UNAVAILABLE"
class Obs(str, Enum): EXACT_UNIQUE="EXACT_UNIQUE"; AMBIGUOUS="AMBIGUOUS"; NOT_FOUND="NOT_FOUND"; UNAVAILABLE="UNAVAILABLE"
class ReturnObs(str, Enum): EXACT_UNIQUE="EXACT_UNIQUE"; AMBIGUOUS="AMBIGUOUS"; VERIFIED_EMPTY="VERIFIED_EMPTY"; NOT_FOUND="NOT_FOUND"; UNAVAILABLE="UNAVAILABLE"

@dataclass(frozen=True)
class Case:
    name: str
    authority: Authority = Authority.VERIFIED
    entitlement_cents: int = 10000
    currency: str = "USD"
    provider: Provider = Provider.CONFIRMED
    send_attempts: int = 1
    settlement_obs: Obs = Obs.EXACT_UNIQUE
    settlement_coverage: Coverage = Coverage.VERIFIED_WINDOW
    amount_match: bool = True
    currency_match: bool = True
    time_match: bool = True
    return_obs: ReturnObs = ReturnObs.VERIFIED_EMPTY
    return_coverage: Coverage = Coverage.VERIFIED_WINDOW
    return_identity_replayed: bool = False
    provider_contradiction_after_refusal: bool = False

def evaluate(c: Case):
    if c.authority != Authority.VERIFIED:
        return {"case":c.name,"classification":"REVIEW_AUTHORITY","claim_locked":False,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":["authority_unverified"]}
    if c.provider == Provider.NOT_SENT:
        return {"case":c.name,"classification":"OWED_NOT_SENT","claim_locked":True,"retry_allowed":True,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":[]}
    if c.provider == Provider.UNKNOWN:
        reasons=["provider_outcome_unknown"] + (["duplicate_send_attempt_blocked"] if c.send_attempts > 1 else [])
        return {"case":c.name,"classification":"PROVIDER_UNKNOWN_HOLD","claim_locked":True,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":reasons}
    if c.provider == Provider.DEFINITE_REFUSAL:
        if c.provider_contradiction_after_refusal:
            return {"case":c.name,"classification":"PROVIDER_CONTRADICTION_REVIEW","claim_locked":True,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":["definite_refusal_later_contradicted"]}
        return {"case":c.name,"classification":"PROVIDER_REFUSED_RELEASED","claim_locked":False,"retry_allowed":True,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":["definite_refusal"]}
    if c.settlement_coverage != Coverage.VERIFIED_WINDOW:
        return {"case":c.name,"classification":"BANK_COVERAGE_UNVERIFIED","claim_locked":True,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":[f"settlement_coverage_{c.settlement_coverage.value.lower()}"]}
    if c.settlement_obs != Obs.EXACT_UNIQUE:
        cls={Obs.AMBIGUOUS:"BANK_MATCH_AMBIGUOUS",Obs.NOT_FOUND:"BANK_NOT_FOUND",Obs.UNAVAILABLE:"BANK_UNAVAILABLE"}[c.settlement_obs]
        return {"case":c.name,"classification":cls,"claim_locked":True,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":[f"settlement_obs_{c.settlement_obs.value.lower()}"]}
    if not (c.amount_match and c.currency_match and c.time_match):
        reasons=[]
        if not c.amount_match: reasons.append("amount_mismatch")
        if not c.currency_match: reasons.append("currency_mismatch")
        if not c.time_match: reasons.append("time_incompatible")
        return {"case":c.name,"classification":"BANK_ECONOMIC_IDENTITY_MISMATCH","claim_locked":True,"retry_allowed":False,"observed_settlement":False,"realized_cents":0,"counterevent_cents":0,"reasons":reasons}
    if c.return_obs == ReturnObs.EXACT_UNIQUE:
        counter=0 if c.return_identity_replayed else -c.entitlement_cents
        return {"case":c.name,"classification":"SETTLEMENT_REVOKED_BY_RETURN","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":0,"counterevent_cents":counter,"reasons":["duplicate_return_counterevent_suppressed"] if c.return_identity_replayed else ["exact_return"]}
    if c.return_obs == ReturnObs.AMBIGUOUS:
        return {"case":c.name,"classification":"RETURN_AMBIGUOUS_REVIEW","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":0,"counterevent_cents":0,"reasons":["ambiguous_return_does_not_auto_unwind"]}
    if c.return_coverage != Coverage.VERIFIED_WINDOW:
        return {"case":c.name,"classification":"RETURN_WINDOW_UNVERIFIED","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":0,"counterevent_cents":0,"reasons":[f"return_coverage_{c.return_coverage.value.lower()}"]}
    if c.return_obs == ReturnObs.VERIFIED_EMPTY:
        return {"case":c.name,"classification":"REALIZED_SETTLED","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":c.entitlement_cents,"counterevent_cents":0,"reasons":[]}
    if c.return_obs == ReturnObs.NOT_FOUND:
        return {"case":c.name,"classification":"RETURN_NOT_FOUND_NOT_PROOF","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":0,"counterevent_cents":0,"reasons":["not_found_without_verified_empty_receipt"]}
    return {"case":c.name,"classification":"RETURN_SOURCE_UNAVAILABLE","claim_locked":True,"retry_allowed":False,"observed_settlement":True,"realized_cents":0,"counterevent_cents":0,"reasons":["return_source_unavailable"]}

CASES=[
    Case("happy_path_realized"),
    Case("authority_unknown",authority=Authority.REVIEW),
    Case("provider_unknown_no_retry",provider=Provider.UNKNOWN),
    Case("provider_unknown_duplicate_send_attempt",provider=Provider.UNKNOWN,send_attempts=2),
    Case("definite_refusal_releases",provider=Provider.DEFINITE_REFUSAL),
    Case("refusal_later_contradicted",provider=Provider.DEFINITE_REFUSAL,provider_contradiction_after_refusal=True),
    Case("duplicate_trace_ambiguous",settlement_obs=Obs.AMBIGUOUS),
    Case("provider_complete_bank_absent",settlement_obs=Obs.NOT_FOUND),
    Case("bank_source_unavailable",settlement_obs=Obs.UNAVAILABLE),
    Case("stale_bank_cursor",settlement_coverage=Coverage.STALE),
    Case("partial_bank_window",settlement_coverage=Coverage.PARTIAL),
    Case("unparseable_amount",amount_match=False),
    Case("wrong_currency",currency_match=False),
    Case("time_outside_window",time_match=False),
    Case("bank_posted_then_returned",return_obs=ReturnObs.EXACT_UNIQUE),
    Case("duplicate_semantic_return",return_obs=ReturnObs.EXACT_UNIQUE,return_identity_replayed=True),
    Case("ambiguous_return",return_obs=ReturnObs.AMBIGUOUS),
    Case("return_source_unavailable",return_obs=ReturnObs.UNAVAILABLE,return_coverage=Coverage.UNAVAILABLE),
    Case("return_window_stale",return_obs=ReturnObs.NOT_FOUND,return_coverage=Coverage.STALE),
    Case("not_found_without_verified_empty",return_obs=ReturnObs.NOT_FOUND),
    Case("equal_total_swapped_identities",settlement_obs=Obs.AMBIGUOUS),
    Case("substring_reference_collision",settlement_obs=Obs.AMBIGUOUS),
    Case("first_unmatched_row_trap",settlement_obs=Obs.AMBIGUOUS),
    Case("verified_empty_return_window",return_obs=ReturnObs.VERIFIED_EMPTY,return_coverage=Coverage.VERIFIED_WINDOW),
]

EXPECTED={
    "happy_path_realized":("REALIZED_SETTLED",10000),"authority_unknown":("REVIEW_AUTHORITY",0),"provider_unknown_no_retry":("PROVIDER_UNKNOWN_HOLD",0),"provider_unknown_duplicate_send_attempt":("PROVIDER_UNKNOWN_HOLD",0),"definite_refusal_releases":("PROVIDER_REFUSED_RELEASED",0),"refusal_later_contradicted":("PROVIDER_CONTRADICTION_REVIEW",0),"duplicate_trace_ambiguous":("BANK_MATCH_AMBIGUOUS",0),"provider_complete_bank_absent":("BANK_NOT_FOUND",0),"bank_source_unavailable":("BANK_UNAVAILABLE",0),"stale_bank_cursor":("BANK_COVERAGE_UNVERIFIED",0),"partial_bank_window":("BANK_COVERAGE_UNVERIFIED",0),"unparseable_amount":("BANK_ECONOMIC_IDENTITY_MISMATCH",0),"wrong_currency":("BANK_ECONOMIC_IDENTITY_MISMATCH",0),"time_outside_window":("BANK_ECONOMIC_IDENTITY_MISMATCH",0),"bank_posted_then_returned":("SETTLEMENT_REVOKED_BY_RETURN",0),"duplicate_semantic_return":("SETTLEMENT_REVOKED_BY_RETURN",0),"ambiguous_return":("RETURN_AMBIGUOUS_REVIEW",0),"return_source_unavailable":("RETURN_WINDOW_UNVERIFIED",0),"return_window_stale":("RETURN_WINDOW_UNVERIFIED",0),"not_found_without_verified_empty":("RETURN_NOT_FOUND_NOT_PROOF",0),"equal_total_swapped_identities":("BANK_MATCH_AMBIGUOUS",0),"substring_reference_collision":("BANK_MATCH_AMBIGUOUS",0),"first_unmatched_row_trap":("BANK_MATCH_AMBIGUOUS",0),"verified_empty_return_window":("REALIZED_SETTLED",10000)
}

def failures(fn):
    out=[]
    for c in CASES:
        got=fn(c); pair=(got["classification"],got["realized_cents"])
        if pair != EXPECTED[c.name]: out.append((c.name,EXPECTED[c.name],pair))
    return out

def mutate_provider_finality(c):
    if c.authority==Authority.VERIFIED and c.provider==Provider.CONFIRMED: return {"case":c.name,"classification":"REALIZED_SETTLED","realized_cents":c.entitlement_cents}
    return evaluate(c)
def mutate_ambiguous_first(c):
    if c.settlement_obs==Obs.AMBIGUOUS: return evaluate(Case(**{**asdict(c),"settlement_obs":Obs.EXACT_UNIQUE}))
    return evaluate(c)
def mutate_cursor_complete(c):
    if c.settlement_coverage in (Coverage.STALE,Coverage.PARTIAL,Coverage.INITIALIZING): return evaluate(Case(**{**asdict(c),"settlement_coverage":Coverage.VERIFIED_WINDOW}))
    return evaluate(c)
def mutate_notfound_empty(c):
    if c.return_obs==ReturnObs.NOT_FOUND: return evaluate(Case(**{**asdict(c),"return_obs":ReturnObs.VERIFIED_EMPTY,"return_coverage":Coverage.VERIFIED_WINDOW}))
    return evaluate(c)
def mutate_ignore_return(c):
    if c.authority==Authority.VERIFIED and c.provider==Provider.CONFIRMED and c.settlement_obs==Obs.EXACT_UNIQUE and c.settlement_coverage==Coverage.VERIFIED_WINDOW and c.amount_match and c.currency_match and c.time_match: return {"case":c.name,"classification":"REALIZED_SETTLED","realized_cents":c.entitlement_cents}
    return evaluate(c)
def mutate_amount_only(c):
    if c.authority==Authority.VERIFIED and c.provider==Provider.CONFIRMED and c.settlement_coverage==Coverage.VERIFIED_WINDOW and c.amount_match: return {"case":c.name,"classification":"REALIZED_SETTLED","realized_cents":c.entitlement_cents}
    return evaluate(c)

MUTANTS={"provider_status_is_finality":mutate_provider_finality,"ambiguous_first_match":mutate_ambiguous_first,"cursor_continuity_equals_completeness":mutate_cursor_complete,"not_found_equals_verified_empty":mutate_notfound_empty,"ignore_later_return":mutate_ignore_return,"amount_only_identity":mutate_amount_only}

@dataclass
class ClaimLedger:
    claimed: bool=False
    sent: bool=False
    return_ids: set=field(default_factory=set)
    counterevent_cents: int=0
    lock: threading.Lock=field(default_factory=threading.Lock)
    def claim_and_send(self):
        with self.lock:
            if self.claimed: return False
            self.claimed=True
        time.sleep(random.random()*0.001)
        with self.lock: self.sent=True
        return True
    def apply_return(self,return_id,cents):
        with self.lock:
            if return_id in self.return_ids: return False
            self.return_ids.add(return_id); self.counterevent_cents-=cents; return True

def race_test(n=200):
    violations=0
    for _ in range(n):
        l=ClaimLedger(); res=[]
        ts=[threading.Thread(target=lambda:res.append(l.claim_and_send())) for __ in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
        if sum(bool(x) for x in res)!=1 or not l.sent: violations+=1
    return violations

if __name__ == "__main__":
    base=failures(evaluate)
    assert not base, base
    killed={name:[x[0] for x in failures(fn)] for name,fn in MUTANTS.items()}
    assert all(killed.values()), killed
    assert race_test(200)==0
    l=ClaimLedger(claimed=True,sent=True)
    assert l.apply_return("ret-1",10000) is True
    assert l.apply_return("ret-1",10000) is False
    assert l.counterevent_cents==-10000
    results=[evaluate(c) for c in CASES]
    digest=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps({"cases":len(CASES),"base_failures":len(base),"mutants_killed":{k:len(v) for k,v in killed.items()},"race_iterations":200,"race_violations":0,"duplicate_return_counterevents":1,"result_sha256":digest},sort_keys=True))
