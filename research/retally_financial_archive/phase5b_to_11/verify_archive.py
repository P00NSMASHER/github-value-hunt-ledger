#!/usr/bin/env python3
"""Verify immutable archived source bytes without executing old software."""
import json
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[3]
PREFIX="research/retally_financial_archive/phase5b_to_11/"
def main():
    doc=json.loads((ROOT/PREFIX/"SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert doc["authority"]=="HISTORICAL_RESEARCH_ONLY_NO_CUSTOMER_OR_FINANCIAL_RELEASE"
    assert doc["batch"]=="phase5b_to_11" and doc["archive_draft_only"] is True
    assert doc["source_file_count"]==112 and doc["source_pr_count"]==13
    originals={r["pr"]:r for r in doc["sources"]}
    assert set(originals)==set([306,308,309,310,312,314,315,316,318,322,325,328,331])
    assert len(doc["artifacts"])==len({r["archived_path"] for r in doc["artifacts"]})
    for item in doc["artifacts"]:
        assert item["pr"] in originals and item["head"]==originals[item["pr"]]["head"]
        assert item["status"] in ("added","modified") and re.fullmatch(r"[a-f0-9]{40}",item["sha"])
        name=PREFIX+"sources/pr-"+str(item["pr"])+"/"+item["original_path"]
        assert name==item["archived_path"] and all(x not in ("",".","..") for x in Path(name).parts)
        source=ROOT/name
        assert source.is_file(),name
        digest=subprocess.run(["git","hash-object","--",str(source)],cwd=ROOT,check=True,
                              capture_output=True,text=True,timeout=15).stdout.strip()
        assert digest==item["sha"],name
    print("PASS: 112 historical financial proof/staging blobs preserved inertly from 13 drafts")
if __name__=="__main__":
    main()
