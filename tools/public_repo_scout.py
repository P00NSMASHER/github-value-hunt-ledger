#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, math, os, pathlib, time, urllib.error, urllib.parse, urllib.request

API="https://api.github.com"
UA="github-value-hunt-ledger-public-scout/1.0"
RISK=("credential stealer","password stealer","token grabber","cookie stealer","session hijacker","phishing kit","ransomware builder","exploit kit","keylogger builder","remote access trojan","botnet builder")
ROOT_WEIGHTS={"src":3,"lib":2,"app":2,"tests":4,"test":3,"spec":2,"migrations":3,"schema":3,"schemas":3,".github":2,"dockerfile":2,"docker-compose.yml":2,"docker-compose.yaml":2,"pyproject.toml":2,"package.json":2,"go.mod":2,"cargo.toml":2,"pom.xml":2,"build.gradle":2,"makefile":1}
CORPUS=("hunters","MASTER.md","COMPONENTS.md","DATASETS.md","CAPABILITIES.md","COMBINATIONS.md","REJECTED.md")

def now(): return dt.datetime.now(dt.timezone.utc)
def parse_time(s):
    try: return dt.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except ValueError: return None
def risk_flags(repo):
    text=" ".join([str(repo.get("name") or ""),str(repo.get("description") or "")," ".join(repo.get("topics") or [])]).lower()
    return [x for x in RISK if x in text]
def root_score(names):
    n={str(x).lower() for x in names}; hits=[]; score=0
    for k,w in ROOT_WEIGHTS.items():
        if k in n: hits.append(k); score+=w
    return min(score,18),sorted(hits)
def recency(pushed):
    p=parse_time(pushed)
    if not p: return 0
    d=max(0,(now()-p).days)
    return 15 if d<=30 else 12 if d<=180 else 8 if d<=730 else 5 if d<=1825 else 2
def triage(repo,names):
    stars=max(0,int(repo.get("stargazers_count") or 0)); forks=max(0,int(repo.get("forks_count") or 0)); size=max(0,int(repo.get("size") or 0))
    rs,hits=root_score(names)
    c={"stars":min(20,round(math.log10(stars+1)/5*20)),"forks":min(8,round(math.log10(forks+1)/4*8)),"activity":recency(repo.get("pushed_at")),"root_code_signals":rs,"license_metadata":5 if (repo.get("license") or {}).get("spdx_id") else 1,"description":4 if len(str(repo.get("description") or "").strip())>=24 else 1,"topics":min(5,len(repo.get("topics") or [])),"not_archived":5 if not repo.get("archived") else 2,"substantive_size":4 if 50<=size<=500000 else 2 if size>0 else 0}
    return min(100,sum(c.values())),c,hits
def corpus_text(root):
    chunks=[]
    for item in CORPUS:
        p=root/item
        paths=p.rglob("*.md") if p.is_dir() else [p] if p.is_file() else []
        for f in paths:
            try:
                if f.stat().st_size<=2_000_000: chunks.append(f.read_text(encoding="utf-8",errors="ignore").lower())
            except OSError: pass
    return "\n".join(chunks)
def known(corpus,repo,sha): return repo.lower() in corpus and sha.lower() in corpus
def queued_pairs(root):
    pairs=set()
    if not root.exists(): return pairs
    for p in root.glob("HUNTER-*.json"):
        try: d=json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        for c in d.get("candidates") or []:
            repo=str(c.get("repository") or "").lower()
            sha=str(c.get("exact_revision") or "").lower()
            if repo and sha: pairs.add((repo,sha))
    return pairs

class GH:
    def __init__(self,token):
        if not token: raise ValueError("GITHUB_TOKEN or GH_TOKEN is required")
        self.token=token
        self.stats={"api_requests":0,"retries":0,"rate_limit_sleeps":0,"revision_cache_hits":0,"root_cache_hits":0,"known_revision_skips":0}
        self._revision_cache={}
        self._root_cache={}
    def get(self,path,q=None):
        url=API+path+("?" + urllib.parse.urlencode(q) if q else "")
        req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {self.token}","X-GitHub-Api-Version":"2022-11-28","User-Agent":UA})
        for attempt in range(3):
            self.stats["api_requests"]+=1
            try:
                with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                body=e.read().decode(errors="replace")[:300]
                retryable=e.code in (403,429) or 500<=e.code<600
                if retryable and attempt<2:
                    remaining=e.headers.get("X-RateLimit-Remaining")
                    reset=e.headers.get("X-RateLimit-Reset")
                    retry_after=e.headers.get("Retry-After")
                    sleep_s=None
                    if retry_after:
                        try: sleep_s=max(0.0,min(float(retry_after),30.0))
                        except ValueError: pass
                    if sleep_s is None and remaining=="0" and reset:
                        try:
                            wait=float(reset)-time.time()+1.0
                            if wait>30.0: raise RuntimeError(f"GitHub API {e.code}: rate limit reset is more than 30s away")
                            sleep_s=max(1.0,wait)
                        except ValueError: pass
                    if sleep_s is None: sleep_s=min(2**attempt,8)
                    self.stats["retries"]+=1
                    if e.code in (403,429): self.stats["rate_limit_sleeps"]+=1
                    time.sleep(sleep_s)
                    continue
                raise RuntimeError(f"GitHub API {e.code}: {body}") from e
        raise RuntimeError("GitHub API retry loop exhausted")
    def search(self,q,sort="updated",per_page=8): return list(self.get("/search/repositories",{"q":q,"sort":sort,"order":"desc","per_page":per_page}).get("items") or [])
    def revision(self,full,branch):
        key=(full,branch)
        if key in self._revision_cache:
            self.stats["revision_cache_hits"]+=1
            return self._revision_cache[key]
        o,r=full.split("/",1); sha=self.get(f"/repos/{o}/{r}/commits/{urllib.parse.quote(branch,safe='')}").get("sha")
        self._revision_cache[key]=sha
        return sha
    def root(self,full,branch):
        key=(full,branch)
        if key in self._root_cache:
            self.stats["root_cache_hits"]+=1
            return self._root_cache[key]
        o,r=full.split("/",1); x=self.get(f"/repos/{o}/{r}/contents",{"ref":branch}); names=[str(i.get("name") or "") for i in x] if isinstance(x,list) else []
        self._root_cache[key]=names
        return names

def candidate(gh,repo,q,corp,own,prior_pairs=None):
    full=str(repo.get("full_name") or "")
    if not full or full.lower()==own.lower(): return None
    rf=risk_flags(repo)
    if rf: return {"repository":full,"url":repo.get("html_url"),"status":"RISK_REVIEW_ONLY","risk_flags":rf,"discovery_query":q}
    branch=str(repo.get("default_branch") or "main")
    try: sha=gh.revision(full,branch)
    except RuntimeError: return None
    if not sha: return None
    pair=(full.lower(),sha.lower())
    if pair in (prior_pairs or set()) or known(corp,full,sha):
        if hasattr(gh,"stats"): gh.stats["known_revision_skips"]=int(gh.stats.get("known_revision_skips",0))+1
        return None
    try: names=gh.root(full,branch)
    except RuntimeError: return None
    score,parts,hits=triage(repo,names); lic=(repo.get("license") or {}).get("spdx_id") or "UNKNOWN"
    return {"repository":full,"url":repo.get("html_url"),"exact_revision":sha,"default_branch":branch,"description":repo.get("description"),"primary_language":repo.get("language"),"topics":repo.get("topics") or [],"published_license_spdx":lic,"stars":int(repo.get("stargazers_count") or 0),"forks":int(repo.get("forks_count") or 0),"archived":bool(repo.get("archived")),"pushed_at":repo.get("pushed_at"),"size_kb":int(repo.get("size") or 0),"root_code_signals":hits,"triage_score":score,"triage_components":parts,"discovery_query":q,"status":"PRE_VERIFICATION_CANDIDATE"}

def worker_run(w,gh,corp,own,per_query,max_candidates,prior_pairs=None):
    seen={}; risks=[]; diag=[]; before=dict(gh.stats)
    for q in w.get("queries") or []:
        try: repos=gh.search(q,per_page=per_query)
        except RuntimeError as e: diag.append({"query":q,"error":str(e)}); continue
        diag.append({"query":q,"returned":len(repos)})
        for r in repos:
            c=candidate(gh,r,q,corp,own,prior_pairs)
            if not c: continue
            if c.get("status")=="RISK_REVIEW_ONLY": risks.append(c); continue
            key=(c["repository"],c["exact_revision"])
            if key not in seen or c["triage_score"]>seen[key]["triage_score"]: seen[key]=c
            time.sleep(0.1)
    cs=sorted(seen.values(),key=lambda x:(x["triage_score"],x["stars"]),reverse=True)[:max_candidates]
    api_metrics={k:int(gh.stats.get(k,0))-int(before.get(k,0)) for k in gh.stats}
    return {"schema_version":2,"generated_at":now().isoformat(),"worker_id":w["id"],"catalogs":w.get("catalogs") or [],"mission":w.get("mission"),"authority":"PRE_VERIFICATION_DISCOVERY_ONLY","candidate_count":len(cs),"candidates":cs,"risk_review_count":len(risks),"risk_review":risks[:20],"search_diagnostics":diag,"api_metrics":api_metrics}

def integrate(root,out):
    merged={}; workers={}; files=sorted(root.glob("HUNTER-*.json"))
    for p in files:
        try: d=json.loads(p.read_text())
        except Exception: continue
        wid=str(d.get("worker_id") or p.stem)
        for c in d.get("candidates") or []:
            key=(str(c.get("repository") or ""),str(c.get("exact_revision") or ""))
            if not all(key): continue
            if key not in merged or int(c.get("triage_score") or 0)>int(merged[key].get("triage_score") or 0): merged[key]=c
            workers.setdefault(key,set()).add(wid)
    ranked=sorted(merged.items(),key=lambda kv:(int(kv[1].get("triage_score") or 0),int(kv[1].get("stars") or 0)),reverse=True)
    lines=["# Automated Scout Digest","","**Authority:** PRE-VERIFICATION DISCOVERY ONLY. This file never promotes directly to MASTER.","",f"Generated: {now().isoformat()}",f"Queue snapshots read: {len(files)}",f"Unique exact-revision candidates: {len(ranked)}","","| Triage | Repository | Exact revision | License | Workers | Description |","|---:|---|---|---|---|---|"]
    for key,c in ranked[:75]:
        repo,sha=key; desc=str(c.get("description") or "").replace("|","\\|").replace("\n"," ")[:180]; ws=", ".join(sorted(workers[key]))
        lines.append(f"| {c.get('triage_score',0)} | [{repo}]({c.get('url')}) | {sha[:12]} | {c.get('published_license_spdx','UNKNOWN')} | {ws} | {desc} |")
    lines += ["","## Promotion rule","","Candidates must still follow the existing worker runbook: exact-revision deep inspection, evidence beyond README where practical, safety/rights review, immutable run submission, verifier handling and integrator review.",""]
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines)); return len(ranked)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",default="automation/hunter_schedule.json"); ap.add_argument("--worker"); ap.add_argument("--integrate",action="store_true"); ap.add_argument("--queue-root",default="intelligence/scout_queue"); ap.add_argument("--output",default="automation/SCOUT_DIGEST.md"); ap.add_argument("--per-query",type=int,default=8); ap.add_argument("--max-candidates",type=int,default=16); ap.add_argument("--own-repo",default=os.environ.get("GITHUB_REPOSITORY","P00NSMASHER/github-value-hunt-ledger")); a=ap.parse_args()
    root=pathlib.Path.cwd(); qr=root/a.queue_root
    if a.integrate: print(f"Integrated {integrate(qr,root/a.output)} candidates"); return
    if not a.worker: ap.error("--worker required unless --integrate")
    m=json.loads((root/a.manifest).read_text()); ws=m.get("workers") or []
    if a.worker!="ALL": ws=[w for w in ws if w.get("id")==a.worker]
    if not ws: raise SystemExit(f"Unknown worker {a.worker}")
    gh=GH(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""); corp=corpus_text(root); prior_pairs=queued_pairs(qr)
    for w in ws:
        d=worker_run(w,gh,corp,a.own_repo,max(1,min(a.per_query,25)),max(1,min(a.max_candidates,100)),prior_pairs)
        p=qr/f"{w['id']}.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n"); print(f"{w['id']}: {d['candidate_count']} candidates")

if __name__=="__main__": main()
