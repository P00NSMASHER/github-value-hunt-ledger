"""Boot a clean, credential-free synthetic Postmill proof from an already built pin."""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from retally_postmill import ACCOUNT, CATALOG, PIN, PrivateDraftPort, open_calendar, seed_calendar, sync_draft, current, review, revise, check_publish, checkpoint_drafts


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--pg-bin", type=Path, required=True)
    p.add_argument("--pg-share", type=Path, required=True)
    p.add_argument("--redis", type=Path, required=True)
    args = p.parse_args()
    upstream, state = args.upstream.resolve(), args.state.resolve()
    pg = args.pg_bin.resolve()
    if subprocess.check_output(["git","-C",str(upstream),"rev-parse","HEAD"],text=True).strip() != PIN:
        sys.exit("Wrong upstream revision")
    if subprocess.call(["git","-C",str(upstream),"diff","--quiet","HEAD","--"]):
        sys.exit("Tracked upstream files have local changes")
    if state.exists():
        sys.exit("Use a new private directory for each run")
    os.umask(0o077)
    state.mkdir(parents=True)
    log = (state/"proof.log").open("w")
    node = shutil.which("node")
    if not node:
        sys.exit("Node 24 is required")
    password, cache_pass, key, jwt = (secrets.token_hex(32) for _ in range(4))
    key = "pm_live_" + key
    env = {"PATH":os.environ["PATH"], "HOME":str(state), "TZ":"UTC", "LANG":"C",
           "LD_LIBRARY_PATH":os.environ.get("LD_LIBRARY_PATH",""),
           "PGPASSWORD":password, "DATABASE_URL":f"postgresql://{os.environ.get('USER','agent')}:{password}@127.0.0.1:55439/retally_postmill_pilot",
           "REDIS_URL":f"redis://:{cache_pass}@127.0.0.1:56379", "JWT_SECRET":jwt,
           "MAIN_URL":"http://127.0.0.1:54971","FRONTEND_URL":"http://127.0.0.1:54971",
           "NEXT_PUBLIC_BACKEND_URL":"http://127.0.0.1:54971", "BACKEND_INTERNAL_URL":"http://127.0.0.1:54971",
           "BACKEND_LISTEN_HOST":"127.0.0.1","PORT":"54971","IS_GENERAL":"true",
           "DISABLE_REGISTRATION":"true","NODE_ENV":"production","USE_INNGEST":"false",
           "INNGEST_DEV":"1","INNGEST_BASE_URL":"http://127.0.0.1:54972",
           "DEV_DISABLE_OPENTELEMETRY":"true","DEV_DISABLE_SENTRY":"true",
           "UPLOAD_DIRECTORY":str(state/"uploads"),"DISABLE_X_ANALYTICS":"true",
           "COPILOTKIT_TELEMETRY_DISABLED":"true","CHECKPOINT_DISABLE":"1","DO_NOT_TRACK":"1"}
    pwfile=state/"pgpass"
    pwfile.write_text(password)
    run([pg/"initdb","-D",state/"postgres","-L",args.pg_share.resolve(),"--locale=C",
         "--encoding=UTF8","--auth=scram-sha-256","--pwfile",pwfile],
        env={**env,"USER":os.environ.get("USER","agent")},stdout=log,stderr=log)
    pwfile.unlink()
    with (state/"postgres/postgresql.conf").open("a") as conf:
        conf.write("\nlisten_addresses='127.0.0.1'\nport=55439\nunix_socket_directories=''\n")
    conf=state/"redis.conf"
    conf.write_text(f"bind 127.0.0.1\nport 56379\nrequirepass {cache_pass}\nappendonly yes\ndir {state}\n")
    db = open_calendar(state/"calendar.sqlite")
    seed_calendar(db)
    sql = """
    BEGIN;
    INSERT INTO "Organization"(id,name,"updatedAt") VALUES('retally-org','RETALLY synthetic',now());
    INSERT INTO "User"(id,email,"providerName","updatedAt") VALUES('retally-user','pilot@example.invalid','LOCAL',now());
    INSERT INTO "UserOrganization"(id,"userId","organizationId","updatedAt") VALUES('retally-member','retally-user','retally-org',now());
    INSERT INTO "ApiKey"(id,"organizationId","userId",name,"hashedKey",prefix,"updatedAt")
        VALUES('retally-key','retally-org','retally-user','disabled integration pilot',:'hash','pm_live_',now());
    INSERT INTO "OrgProviderConfiguration"(id,"organizationId",identifier,name,enabled,"updatedAt")
        VALUES('retally-fixture-provider','retally-org','instagram-standalone','Synthetic draft adapter',true,now());
    INSERT INTO "Integration"(id,"internalId","organizationId",name,"providerIdentifier",type,token,disabled,"updatedAt")
        VALUES(:'account',:'account','retally-org','RETALLY TEST','instagram-standalone','social','',true,now());
    COMMIT;
    """
    processes = []
    def start(cmd, cwd, suffix):
        with (state/suffix).open("a") as sink:
            child=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=sink,stderr=subprocess.STDOUT)
        processes.append(child)
        return child

    def stop(child):
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()

    class ProofPort(PrivateDraftPort):
        writes = 0
        lost_response = False
        def _error(self, method, path, response):
            print(response.read(1200).decode(errors="replace"), file=log, flush=True)
            super()._error(method, path, response)

        def _call(self, method, path, data=None, key=None):
            try:
                result = super()._call(method, path, data, key)
            except RuntimeError as err:
                print(str(err), file=log, flush=True)
                raise
            if method == "POST" or path.startswith("posts?"):
                print(method, path.split("?")[0], json.dumps(result), file=log, flush=True)
            if method == "POST":
                self.writes += 1
                if not self.lost_response:
                    self.lost_response = True
                    raise TimeoutError("Injected response loss after the real Postmill commit")
            return result
    api=ProofPort(54971,key)
    try:
        start([pg/"postgres","-D",state/"postgres"],state,"postgres.log")
        cache=start([args.redis.absolute(),conf],state,"redis.log")
        for _ in range(50):
            if subprocess.run([pg/"pg_isready","-h","127.0.0.1","-p","55439"],stdout=log,stderr=log).returncode==0:
                break
            time.sleep(.15)
        pgargs=["-h","127.0.0.1","-p","55439"]
        run([pg/"createdb",*pgargs,"retally_postmill_pilot"],env=env,stdout=log,stderr=log)
        prisma=upstream/"node_modules/prisma/build/index.js"
        schema=upstream/"libraries/nestjs-libraries/src/database/prisma/schema.prisma"
        run([node,prisma,"migrate","deploy","--schema",schema],env=env,cwd=upstream,stdout=log,stderr=log)
        def psql(args,**kw):
            return run([pg/"psql",*pgargs,"-d","retally_postmill_pilot","-v","ON_ERROR_STOP=1",*args],
                       env=env,text=True,stderr=log,**kw)
        psql(["-v","hash="+hashlib.sha256(key.encode()).hexdigest(),"-v","account="+ACCOUNT],input=sql,stdout=log)
        def launch():
            proc=start([node,"--experimental-require-module","-r",str(upstream/"apps/backend/register-paths.cjs"),"apps/backend/dist/apps/backend/src/main.js"],upstream,"backend.log")
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Postmill exited. See backend.log")
                try:
                    api.assert_isolated()
                    return proc
                except (OSError,RuntimeError):
                    time.sleep(.3)
            raise RuntimeError("Postmill HTTP readiness timed out")
        backend=launch()
        first={slug:sync_draft(db,slug,api) for slug in CATALOG}
        review(db,"liftgate_evidence")
        review(db,"liftgate_evidence",approve=True)
        sealed=current(db,"liftgate_evidence")["approval"]
        revise(db,"liftgate_evidence",2)
        before=api.writes
        try:
            check_publish(db,"liftgate_evidence",sealed)
            raise AssertionError("Stale approval accepted")
        except PermissionError as err:
            if "expired" not in str(err): raise
        if api.writes!=before or sync_draft(db,"liftgate_evidence",api)!=first["liftgate_evidence"]:
            raise AssertionError("Revision changed draft identity or allowed publishing")
        stop(backend)
        stop(cache)
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1",56379)) == 0:
                raise AssertionError("Redis still accepting connections")
        empty=state/"empty-cache"
        empty.mkdir()
        conf.write_text(f"bind 127.0.0.1\nport 56379\nrequirepass {cache_pass}\nappendonly yes\ndir {empty}\n")
        start([args.redis.absolute(),conf],state,"redis.log")
        db.close()
        db=open_calendar(state/"calendar.sqlite")
        launch()
        before=api.writes
        after={slug:sync_draft(db,slug,api) for slug in CATALOG}
        counts=psql(["-Atc",'SELECT state,count(*) FROM "Post" GROUP BY state ORDER BY state'],capture_output=False,stdout=subprocess.PIPE).stdout.strip()
        if first!=after or counts!="DRAFT|3" or api.writes != before:
            raise RuntimeError("Post-restart proof mismatch")
        result={"environment":"local pinned Postmill","sha":PIN,"draft_ids_after_restart":after,
                "database_state_counts":counts,"integration":ACCOUNT,"disabled":True,
                "publish_credentials":False, "actual_platform_metrics":None, "postmill_calls_other_than_draft_writes_and_reads":0,
                "redis_outage_and_empty_restart":True, "draft_writes_after_restart":api.writes-before,
                "revoked_approval_publish_attempts":0, "committed_response_loss_injected":api.lost_response,
                "updated_draft_id_preserved":True, "draft_write_attempts":db.execute("SELECT sum(attempts) FROM social_dispatch").fetchone()[0]}
        result["drafts"] = checkpoint_drafts(db)
        (state/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result))
    finally:
        for child in reversed(processes): stop(child)
        db.close()
        log.close()
        conf.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
