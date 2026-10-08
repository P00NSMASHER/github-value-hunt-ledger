"""Validate RETALLY's stacked research PRs as one *unmerged* integration candidate.

This does not merge, promote, deploy, or change the original finding register.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import re
import subprocess

from freight.lab_assurance import digest

STACK = (
    (279, "b19c27668d0b60096bbe9b1049c32e5d5445dd1a"),
    (284, "b46828dd47486f0911dc040abab8e9ff1b05e170"),
    (286, "27d7c301753bfee24152f950ac48002ef5774236"),
    (288, "e2cb4a4a5d97167bf274d15341fbecc102ae6d5c"),
)
REQUIRED = (
    "freight/research/LAB_FINDINGS_CUMULATIVE.json",
    "freight/research/HUNTED_CODE_REUSE_CANDIDATES.json",
    "freight/lab_assurance.py",
    "freight/lab_phase2_pipeline.py",
    "freight/lab_phase3_economics.py",
    "freight/lab_phase3_integration.py",
    "freight/lab_phase3_simulated_pilot.py",
    "freight/lab_phase3_trust.py",
)


def validate(root: Path, *, check_git_ancestry: bool=False) -> dict:
    for _,sha in STACK:
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise ValueError("bad pinned PR SHA")
    missing=[p for p in REQUIRED if not (root/p).is_file()]
    if missing:
        raise ValueError("MISSING_REQUIRED_CODE:"+",".join(missing))
    raw=json.loads((root/"freight/research/LAB_FINDINGS_CUMULATIVE.json").read_text())
    entries=raw["entries"]
    if len(entries)!=28 or raw["historical_open_findings"]!=26:
        raise ValueError("HISTORICAL_FINDINGS_COUNT_CHANGED")
    if len({x["id"] for x in entries})!=28:
        raise ValueError("DUPLICATED_FINDING_ID")
    original=[x for x in entries if x["remediation"]=="OPEN_UNVERIFIED"]
    if len(original)!=26 or any(x.get("customer_or_production_impact")!="NOT_ESTABLISHED" for x in entries):
        raise ValueError("RESEARCH_CLAIM_BOUNDARY_BROKEN")
    if check_git_ancestry:
        for _,sha in STACK:
            result=subprocess.run(["git","merge-base","--is-ancestor",sha,"HEAD"],
                                  cwd=root,check=False,capture_output=True,text=True)
            if result.returncode!=0:
                raise ValueError("STACK_ANCESTOR_NOT_FOUND:"+sha)
    body={"scope":"UNMERGED_RESEARCH_INTEGRATION_CANDIDATE",
          "pull_request_chain":[{"pr":n,"pinned_head":sha} for n,sha in STACK],
          "original_findings_open":len(original),"verifier_bugs_fixed_in_research_only":2,
          "source_components_present":list(REQUIRED),
          "git_ancestry_checked":check_git_ancestry,
          "production_deployed":False,"merge_performed":False}
    return {**body,"receipt_sha256":digest(body)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--check-git-ancestry",action="store_true")
    args=p.parse_args()
    print(json.dumps(validate(args.root,check_git_ancestry=args.check_git_ancestry),indent=2,sort_keys=True))

if __name__=="__main__":main()
