"""Read-only, fail-closed cumulative Freight lab audit registry check.

The public repository is an index, not proof of actual customer financial results.
This tool checks that historical findings cannot disappear or become 'fixed'
without explicit evidence; it does not install donor code or certify the labs.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import re

DIR=Path(__file__).resolve().parent
ORIGINAL={*[f"LAB-P0-{i:02d}" for i in range(1,5)],
          *[f"LAB-P1-{i:02d}" for i in range(5,8)],"LAB-P2-08",
          *[f"D-{i:02d}" for i in range(1,9)],
          *[f"X-{i:02d}" for i in range(1,6)],
          *[f"Y-{i:02d}" for i in range(1,5)],"Z-01"}
REVISION=re.compile(r"^[0-9a-f]{40}$")
LICENSES={"MIT","Apache-2.0","MIT OR Apache-2.0"}

def validate(ledger:dict, donors:dict)->list[str]:
    errors=[]
    rows=ledger.get("items")
    if not isinstance(rows,list) or not rows:
        return ["CUMULATIVE_REGISTER_EMPTY"]
    ids=[x.get("id") for x in rows if isinstance(x,dict)]
    if len(ids)!=len(rows) or len(set(ids))!=len(ids):
        errors.append("DUPLICATE_OR_INVALID_FINDING_ID")
    missing=ORIGINAL-set(ids)
    if missing:
        errors.append("HISTORICAL_FINDINGS_DISAPPEARED:"+",".join(sorted(missing)))
    if ledger.get("total_observations")!=len(rows):
        errors.append("INCORRECT_FINDING_COUNT")
    groups=Counter(x.get("root_cause_cluster") for x in rows if isinstance(x,dict))
    if dict(groups)!=ledger.get("cluster_counts"):
        errors.append("ROOT_CAUSE_CLUSTER_COUNTS_DIFFER")
    if ledger.get("open_unrepaired_historical")!=sum(
        x.get("remediation")=="OPEN_NOT_FIXED" and x.get("id") in ORIGINAL
        for x in rows if isinstance(x,dict)
    ):
        errors.append("HISTORICAL_OPEN_COUNT_DIFFERS")
    for x in rows:
        if not isinstance(x,dict):continue
        if x.get("remediation","").startswith("FIXED") and not x.get("regression"):
            errors.append("UNVERIFIED_FIXED_FINDING:"+str(x.get("id")))
        if x.get("production_impact")!="NOT_ESTABLISHED":
            errors.append("UNSUPPORTED_PRODUCTION_VULNERABILITY_CLAIM:"+str(x.get("id")))
    candidates=donors.get("candidates")
    if not isinstance(candidates,list) or not candidates:
        errors.append("HUNTED_DONOR_CATALOG_MISSING")
    else:
        for donor in candidates:
            label=donor.get("id","UNKNOWN")
            if not REVISION.fullmatch(str(donor.get("revision",""))):
                errors.append("DONOR_REVISION_NOT_PINNED:"+str(label))
            if donor.get("license") not in LICENSES:
                errors.append("DONOR_LICENSE_UNVERIFIED:"+str(label))
            if donor.get("review_status")!="PINNED_CODE_LICENSE_INSPECTED_NO_CODE_IMPORTED":
                errors.append("DONOR_STATUS_CLAIMS_INTEGRATION:"+str(label))
    if donors.get("code_copied_into_recoveryos") is not False:
        errors.append("UNSUPPORTED_CODE_DEPLOYMENT_CLAIM")
    return errors

def read_reports(root:Path=DIR)->tuple[dict,dict]:
    return (json.loads((root/"CUMULATIVE_FINDINGS.json").read_text(encoding="utf-8")),
            json.loads((root/"HUNTED_DONOR_SHORTLIST.json").read_text(encoding="utf-8")))

def main()->int:
    try:
        ledger,donors=read_reports()
        errors=validate(ledger,donors)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({"state":"INVALID_INPUT","error":str(exc)}))
        return 2
    state="PASS_RESEARCH_REGISTRY_ONLY" if not errors else "FAIL"
    print(json.dumps({"state":state,"finding_count":len(ledger["items"]),
      "historical_observations":26,"donor_candidates":len(donors["candidates"]),
      "errors":errors,"commercial_release":"BLOCKED_UNTIL_SEPARATELY_VERIFIED"},indent=2))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
