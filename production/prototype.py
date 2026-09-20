"""Production-contract prototype for the GitHub Value Hunt.

This is intentionally small and deterministic. It does not run agents; it enforces
trusted-state transitions around evidence, candidate promotion, skill promotion,
and task leases.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable

class CandidateState(str, Enum):
    DISCOVERED="DISCOVERED"; INVESTIGATING="INVESTIGATING"; EVIDENCE_FROZEN="EVIDENCE_FROZEN"
    VERIFICATION_PENDING="VERIFICATION_PENDING"; WATCH="WATCH"; REJECTED="REJECTED"
    STRONG_COMPONENT="STRONG_COMPONENT"; MASTER_CANDIDATE="MASTER_CANDIDATE"; MASTER="MASTER"

class Verdict(str, Enum):
    PASS="PASS"; PASS_WITH_LIMITS="PASS_WITH_LIMITS"; INCOMPLETE="INCOMPLETE"
    CONTRADICTED="CONTRADICTED"; BLOCKED_SAFETY="BLOCKED_SAFETY"; BLOCKED_RIGHTS="BLOCKED_RIGHTS"

class SkillState(str, Enum):
    LOCAL="LOCAL"; STAGED="STAGED"; VERIFIED="VERIFIED"; CANARY="CANARY"; GLOBAL="GLOBAL"
    QUARANTINED="QUARANTINED"; RETIRED="RETIRED"

@dataclass(frozen=True)
class CommercialScore:
    speed_to_revenue:int; value_ceiling:int; build_compression:int
    rarity_advantage:int; evidence_quality:int; rights_operability:int
    def __post_init__(self):
        if any(v < 0 or v > 5 for v in self.values()): raise ValueError("score dimensions must be 0..5")
    def values(self):
        return (self.speed_to_revenue,self.value_ceiling,self.build_compression,self.rarity_advantage,self.evidence_quality,self.rights_operability)
    @property
    def total(self): return sum(self.values())

@dataclass(frozen=True)
class VerificationRecord:
    verdict:Verdict; frozen_snapshot_hash:str|None; blocking_findings:tuple[str,...]=()
    core_claim_readme_only:bool=False; sensitive_source_contamination:bool=False; critical_contradiction:bool=False

@dataclass(frozen=True)
class CandidateRecord:
    candidate_id:str; canonical_uri:str; exact_revision:str|None; score:CommercialScore
    verification:VerificationRecord|None=None; unique_component_reason:str|None=None
    third_party_rights_blocker:bool=False

@dataclass(frozen=True)
class PromotionResult:
    state:CandidateState; reasons:tuple[str,...]=()

@dataclass(frozen=True)
class EvidenceItem:
    evidence_id:str; canonical_source:str; exact_revision:str; locator:str; sha256:str; evidence_type:str
    sensitivity_class:str="NORMAL"; redaction_state:str="NONE"

def _canonical_json(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def freeze_evidence_manifest(candidate_id:str, repository:str, revision:str, claims:Iterable[str], evidence:Iterable[EvidenceItem])->dict:
    if not revision: raise ValueError("exact revision is required")
    body={"schema":1,"candidate_id":candidate_id,"repository":repository,"revision":revision,
          "claims":sorted(set(claims)),"evidence":sorted((asdict(x) for x in evidence),key=lambda x:x["evidence_id"])}
    body["manifest_sha256"]=hashlib.sha256(_canonical_json(body)).hexdigest()
    return body

def verify_manifest(manifest:dict)->bool:
    supplied=manifest.get("manifest_sha256")
    if not supplied: return False
    body=dict(manifest); body.pop("manifest_sha256",None)
    expected=hashlib.sha256(_canonical_json(body)).hexdigest()
    return supplied==expected

def evaluate_promotion(candidate:CandidateRecord)->PromotionResult:
    v=candidate.verification
    if not candidate.exact_revision: return PromotionResult(CandidateState.REJECTED,("missing_exact_revision",))
    if candidate.third_party_rights_blocker: return PromotionResult(CandidateState.REJECTED,("unresolved_third_party_rights_blocker",))
    if v is None: return PromotionResult(CandidateState.VERIFICATION_PENDING,("independent_verifier_required",))
    if not v.frozen_snapshot_hash: return PromotionResult(CandidateState.VERIFICATION_PENDING,("frozen_evidence_snapshot_required",))
    if v.sensitive_source_contamination: return PromotionResult(CandidateState.REJECTED,("sensitive_source_contamination",))
    if v.critical_contradiction: return PromotionResult(CandidateState.REJECTED,("critical_contradiction",))
    if v.core_claim_readme_only: return PromotionResult(CandidateState.WATCH,("core_claim_readme_only",))
    if v.verdict in {Verdict.BLOCKED_SAFETY,Verdict.BLOCKED_RIGHTS,Verdict.CONTRADICTED}:
        return PromotionResult(CandidateState.REJECTED,(f"verifier_{v.verdict.value.lower()}",))
    if v.verdict in {Verdict.INCOMPLETE,Verdict.PASS_WITH_LIMITS}:
        return PromotionResult(CandidateState.WATCH,(f"verifier_{v.verdict.value.lower()}",))
    if v.verdict is not Verdict.PASS: return PromotionResult(CandidateState.WATCH,("verifier_not_passed",))
    s=candidate.score; reasons=[]
    if s.evidence_quality < 4: reasons.append("evidence_quality_below_master_gate")
    if s.rights_operability < 4: reasons.append("rights_operability_below_master_gate")
    if s.total >= 27 and not reasons: return PromotionResult(CandidateState.MASTER_CANDIDATE,())
    if 24 <= s.total <= 26:
        if candidate.unique_component_reason and s.evidence_quality>=4 and s.rights_operability>=4:
            return PromotionResult(CandidateState.STRONG_COMPONENT,("unique_component_requires_integrator_review",))
        return PromotionResult(CandidateState.STRONG_COMPONENT,tuple(reasons or ["score_24_26_component_gate"]))
    if s.total >= 27: return PromotionResult(CandidateState.STRONG_COMPONENT,tuple(reasons))
    if s.total >= 19: return PromotionResult(CandidateState.WATCH,("score_19_23",))
    return PromotionResult(CandidateState.REJECTED,("score_below_19",))

@dataclass(frozen=True)
class SkillVerification:
    distinct_success_task_ids:frozenset[str]=field(default_factory=frozenset)
    heldout_tasks:int=0; heldout_passes:int=0; heldout_regressions:int=0
    adversarial_task_passed:bool=False; adjacent_domain_task_passed:bool=False
    curator_approved:bool=False; canary_hunters:int=0; canary_regressions:int=0
    @property
    def heldout_pass_rate(self): return 0.0 if self.heldout_tasks==0 else self.heldout_passes/self.heldout_tasks

def evaluate_skill_promotion(v:SkillVerification)->tuple[SkillState,tuple[str,...]]:
    n=len(v.distinct_success_task_ids)
    if n<1: return SkillState.LOCAL,("no_observed_success",)
    if n<2: return SkillState.LOCAL,("one_success_local_only",)
    if v.heldout_tasks==0: return SkillState.STAGED,("heldout_verification_required",)
    if v.heldout_tasks<5: return SkillState.STAGED,("minimum_five_heldout_tasks",)
    if v.heldout_pass_rate<1.0 or v.heldout_regressions>0: return SkillState.QUARANTINED,("heldout_failure_or_regression",)
    if not v.adversarial_task_passed: return SkillState.STAGED,("adversarial_task_required",)
    if not v.adjacent_domain_task_passed: return SkillState.STAGED,("adjacent_domain_transfer_required",)
    if not v.curator_approved: return SkillState.VERIFIED,("curator_approval_required_for_global",)
    if v.canary_hunters<3: return SkillState.CANARY,("three_hunter_canary_required",)
    if v.canary_regressions>0: return SkillState.QUARANTINED,("canary_regression",)
    return SkillState.GLOBAL,()

@dataclass(frozen=True)
class Lease:
    task_id:str; owner:str; generation:int; acquired_at:datetime; expires_at:datetime

class LeaseBook:
    def __init__(self): self._leases={}; self._generations={}
    def claim(self,task_id:str,owner:str,ttl_seconds:int,now:datetime|None=None)->Lease|None:
        if ttl_seconds<=0: raise ValueError("ttl_seconds must be positive")
        t=now or datetime.now(timezone.utc); existing=self._leases.get(task_id)
        if existing and existing.expires_at>t and existing.owner!=owner: return None
        gen=self._generations.get(task_id,0)+1; self._generations[task_id]=gen
        lease=Lease(task_id,owner,gen,t,t+timedelta(seconds=ttl_seconds)); self._leases[task_id]=lease; return lease
    def renew(self,task_id:str,owner:str,generation:int,ttl_seconds:int,now:datetime|None=None)->Lease|None:
        t=now or datetime.now(timezone.utc); existing=self._leases.get(task_id)
        if not existing or existing.owner!=owner or existing.generation!=generation or existing.expires_at<=t: return None
        lease=Lease(task_id,owner,generation,existing.acquired_at,t+timedelta(seconds=ttl_seconds)); self._leases[task_id]=lease; return lease
    def release(self,task_id:str,owner:str,generation:int)->bool:
        existing=self._leases.get(task_id)
        if not existing or existing.owner!=owner or existing.generation!=generation: return False
        del self._leases[task_id]; return True
    def recoverable(self,now:datetime|None=None)->list[str]:
        t=now or datetime.now(timezone.utc); return sorted(k for k,v in self._leases.items() if v.expires_at<=t)


class FreightWorkDecision(str, Enum):
    ALLOW="ALLOW"
    DENY="DENY"

@dataclass(frozen=True)
class FreightWorkRequest:
    stage_gate:str
    gap_id:str|None
    trigger:str
    category:str
    evidence_to_change_decision:str
    why_existing_stack_insufficient:str
    stop_condition:str
    broad_search:bool=False

@dataclass(frozen=True)
class FreightWorkResult:
    decision:FreightWorkDecision
    reasons:tuple[str,...]=()

@dataclass(frozen=True)
class FreightGapAuthorization:
    gap_id:str
    status:str
    search_allowed:bool
    allowed_triggers:frozenset[str]=field(default_factory=frozenset)

FREIGHT_ALLOWED_TRIGGERS=frozenset({
    "EXP001_GAP",
    "PAYING_CUSTOMER_GAP",
    "SECURITY_DILIGENCE",
    "RIGHTS_DILIGENCE",
    "INDEPENDENT_FALSIFIER",
    "SETTLEMENT_CONNECTOR",
    "AUTHORITY_CONNECTOR",
})
FREIGHT_BLOCKED_GENERIC_CATEGORIES=frozenset({
    "GENERIC_TMS",
    "GENERIC_OCR",
    "GENERIC_RULES",
    "GENERIC_RATING",
    "GENERIC_DASHBOARD",
    "GENERIC_ENTITY_MATCHER",
})

def evaluate_freight_work_request(
    req:FreightWorkRequest,
    gap:FreightGapAuthorization|None=None,
)->FreightWorkResult:
    reasons=[]
    if gap is None:
        reasons.append("gap_id_not_registered")
    else:
        if req.gap_id != gap.gap_id:
            reasons.append("gap_id_mismatch")
        if gap.status!="ACTIVE_SEARCH":
            reasons.append("registered_gap_not_active_search")
        if not gap.search_allowed:
            reasons.append("registered_gap_search_not_allowed")
        if req.trigger not in gap.allowed_triggers:
            reasons.append("trigger_not_allowed_for_registered_gap")
    if req.stage_gate!="EXP-001":
        reasons.append("freight_work_must_link_to_exp001")
    if not req.gap_id or not req.gap_id.strip():
        reasons.append("named_gap_id_required")
    if req.broad_search:
        reasons.append("broad_freight_search_frozen")
    if req.trigger not in FREIGHT_ALLOWED_TRIGGERS:
        reasons.append("unsupported_freight_trigger")
    if req.category in FREIGHT_BLOCKED_GENERIC_CATEGORIES:
        reasons.append("generic_freight_subsystem_blocked")
    for field_name in (
        "evidence_to_change_decision",
        "why_existing_stack_insufficient",
        "stop_condition",
    ):
        value=getattr(req,field_name)
        if not value or not value.strip():
            reasons.append(f"{field_name}_required")
    if reasons:
        return FreightWorkResult(FreightWorkDecision.DENY,tuple(reasons))
    return FreightWorkResult(FreightWorkDecision.ALLOW,())
