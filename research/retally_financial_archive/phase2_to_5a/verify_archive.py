#!/usr/bin/env python3
"""Verify archived Git object bytes only; never execute archived source."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PREFIX="research/retally_financial_archive/phase2_to_5a/"
MANIFEST=ROOT / PREFIX / "SOURCE_MANIFEST.json"

def main():
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["authority"]=="HISTORICAL_RESEARCH_ONLY_NO_CUSTOMER_OR_FINANCIAL_RELEASE"
    assert m["archive_draft_only"] is True and m["batch"]=="phase2_to_5a"
    assert m["source_pr_count"]==9 and m["source_file_count"]==72
    by_pr={x["pr"]:x for x in m["sources"]}
    assert set(by_pr)==set([284,286,288,295,297,299,301,302,304])
    assert len(m["artifacts"])==len({x["archived_path"] for x in m["artifacts"]})
    for r in m["artifacts"]:
        assert r["pr"] in by_pr and r["head"]==by_pr[r["pr"]]["head"]
        assert re.fullmatch(r"[a-f0-9]{40}",r["sha"])
        assert r["status"] in ("added","modified")
        expected=PREFIX+"sources/pr-"+str(r["pr"])+"/"+r["original_path"]
        assert r["archived_path"]==expected
        assert all(x not in (".","..","") for x in Path(expected).parts)
        file=ROOT / expected
        assert file.is_file(),expected
        got=subprocess.run(["git","hash-object","--",str(file)],cwd=ROOT,check=True,
                           capture_output=True,text=True,timeout=15).stdout.strip()
        assert got==r["sha"],expected
    print("PASS: 72 original financial research blobs preserved with exact SHA, no execution.")

if __name__=="__main__":
    main()
