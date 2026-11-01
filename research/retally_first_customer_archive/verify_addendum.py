"""Verify inert original source Git objects; never execute archived code."""
import json
from pathlib import Path, PurePosixPath
import re, subprocess
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research" / "retally_first_customer_archive"
PREFIX = "research/retally_first_customer_archive/sources/"

def main():
    m=json.loads((BASE/"SOURCE_ADDENDUM.json").read_text(encoding="utf-8"))
    assert m["schema_version"]==1
    assert m["authority"]=="HISTORICAL_SOURCE_ONLY_NOT_PRODUCTION_OR_CUSTOMER_APPROVAL"
    assert m["archive_review_only"] and m["no_live_customer_or_cash_authority"]
    assert m["source_prs"]==[327,461] and len(m["records"])==85
    seen=set()
    for item in m["records"]:
        n=item["pr"]; name=PurePosixPath(item["original_path"])
        assert n in m["source_prs"] and item["pr_head"]==m["source_heads"][str(n)]
        assert re.fullmatch(r"[0-9a-f]{40}",item["blob_sha"])
        assert item["status"] in ("added","modified","removed","renamed")
        assert not name.is_absolute() and all(x not in ("",".","..") for x in name.parts)
        if item["status"]=="removed":
            assert item["archived_path"] is None
            continue
        p=item["archived_path"]
        assert p==PREFIX+f"pr-{n}/"+item["original_path"] and p not in seen
        seen.add(p)
        assert (ROOT/p).is_file()
        sha=subprocess.check_output(["git","rev-parse","HEAD:"+p],cwd=ROOT,text=True).strip()
        assert sha==item["blob_sha"],(p,sha,item["blob_sha"])
        assert subprocess.check_output(["git","cat-file","-t",sha],cwd=ROOT,text=True).strip()=="blob"
    print(f"PASS: {len(seen)} original source blobs retained as inert archive data")

if __name__=="__main__":
    main()
