import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { PGlite } from "@electric-sql/pglite";

const here = fileURLToPath(new URL(".", import.meta.url));
const upstream = resolve(process.argv[2]);
const migrations = resolve(process.argv[3] ?? join(here, "../../supabase/migrations/ai_business_os"));
const root = await mkdtemp(join(tmpdir(), "retally-prime-"));
const work = join(root, "work");
const database = join(root, "state");
const deadline = 25000;
const prompt = "Return a unified diff for create_lead.sql that fixes duplicate inquiry leads after a committed request times out. Include the trusted test command.";
const started = Date.now();

function verifier(diff, args = []) {
    const result = spawnSync("python3", [join(here, "verify.py"), ...args], {
        input: diff, encoding: "utf8", timeout: 5000, maxBuffer: 65536,
    });
    if (result.status !== 0) throw Error(result.stderr || "verifier failed");
    return result.stdout.trim();
}

async function runWorker(claim, killOnAck) {
    const worker = spawn("bash", [join(here, "sandbox.sh"), upstream, work], { stdio: ["pipe", "pipe", "pipe"] });
    const exited = once(worker, "exit");
    const timer = setTimeout(() => worker.kill("SIGKILL"), deadline);
    let stderr = "", line = "", bytes = 0, gotState = false, accepted = false;
    worker.stderr.on("data", chunk => { stderr = (stderr + chunk).slice(-4000); });
    worker.stdin.on("error", error => { if (error.code !== "EPIPE") worker.kill("SIGKILL"); });
    const send = value => worker.stdin.write(JSON.stringify(value) + "\n");
    const id = "fixture-" + claim.lease_generation;
    try {
        send({id: "state", type: "get_state"});
        worker.stdout.setEncoding("utf8");
        for await (const chunk of worker.stdout) {
            bytes += Buffer.byteLength(chunk);
            if (bytes > 1024 * 1024) throw Error("RPC output budget exceeded");
            line += chunk;
            let end;
            while ((end = line.indexOf("\n")) !== -1) {
                const event = JSON.parse(line.slice(0, end));
                line = line.slice(end + 1);
                if (event.type === "response" && event.id === "state") {
                    assert.equal(event.success, true);
                    assert.equal(event.data.model.provider, "retally-replay");
                    assert.match(event.data.sessionFile, /^\/tmp\/home\/sessions\//);
                    gotState = true;
                    send({type: "prompt", id, message: prompt});
                }
                if (event.type === "response" && event.id === id) {
                    assert.equal(event.command, "prompt");
                    assert.equal(event.success, true);
                    accepted = true;
                    if (killOnAck) return {id, accepted, killed_after_ack: true};
                }
                if (event.type === "agent_end") {
                    assert.ok(gotState && accepted);
                    const response = event.messages.findLast(message => message.role === "assistant");
                    assert.equal(response?.stopReason, "stop");
                    const artifact = JSON.parse(response.content.find(block => block.type === "text").text);
                    assert.equal(artifact.test_command, "python3 verify.py");
                    return {id, accepted, artifact};
                }
            }
        }
        throw Error(stderr || "RPC stream ended without required response");
    } finally {
        clearTimeout(timer);
        worker.kill("SIGKILL");
        await exited;
    }
}

let db;
try {
    const base = verifier("", ["--init-fixture", work]);
    db = new PGlite(database);
    const bootstrap = await readFile(join(migrations, "bootstrap.sql"), "utf8");
    await db.exec("CREATE SCHEMA ai_business_os_prod; CREATE ROLE anon; CREATE ROLE authenticated;");
    for (const table of ["agents", "agent_runs", "agent_heartbeats", "agent_goals"]) {
        const ddl = bootstrap.match(new RegExp("^create table if not exists ai_business_os_prod\\." + table + " \\([\\s\\S]+?^\\);", "m"));
        assert.ok(ddl, "missing canonical DDL for " + table);
        await db.exec(ddl[0]);
    }
    const sql = await readFile(join(migrations, "20260925151646_add_ai_business_os_persistent_worker_control_v1.sql"), "utf8");
    const scheduler = sql.lastIndexOf("select cron.schedule(");
    assert.ok(scheduler > 0);
    await db.exec(sql.slice(0, scheduler)); // Local pilot calls the real expiry function directly.
    const schema = "ai_business_os_prod.";
    await db.query("INSERT INTO " + schema + "agents(agent_id,role_key,display_name,objective,memory_scope) VALUES ('pilot','pilot','Pilot','Test','local')");
    await db.query("INSERT INTO " + schema + "agent_goals(agent_id,goal_type,title,constraints,evidence_requirements) VALUES ('pilot','BOUNDED_FIXTURE','Fix timeout',$1,$2)",
        [JSON.stringify({goal: prompt, base_sha: base, allowed_paths: ["create_lead.sql"], model_tools: [],
            wall_ms: deadline, cpu_seconds_per_process: 20, nproc: 128, network: false, incremental_cost: 0}),
         JSON.stringify(["unified diff","clean clone red and green counts","scope and mode check"])]);
    const call = async (name, args) => (await db.query("SELECT " + schema + "agent_worker_" + name + "_v1(" +
        args.map((_, index) => "$" + (index + 1)).join(",") + ") AS data", args)).rows[0].data;
    const claim = owner => call("claim", ["pilot", owner, '["BOUNDED_FIXTURE"]', 30]);
    const submit = (owner, c, output) => call("submit", ["pilot", owner, c.goal.id, c.run_id, c.lease_generation,
        output.diff_sha256, JSON.stringify([output]), "Offline replay verified by independent clean-clone oracle"]);
    const first = await claim("first");
    const interrupted = await runWorker(first, true);
    assert.equal((await claim("replacement")).reason, "agent_busy");
    // Sleep until the real persisted lease expiry, then reopen an independent database session.
    await delay(Math.max(0, Date.parse(first.lease_expires_at) - Date.now() + 100));
    await db.close();
    db = new PGlite(database);
    const second = await claim("replacement");
    assert.equal(second.goal.id, first.goal.id);
    assert.equal(second.lease_generation, first.lease_generation + 1);
    const replay = await runWorker(second, false);
    const change = JSON.parse(verifier(replay.artifact.diff));
    assert.equal(change.fixture_base_sha, base);
    assert.throws(() => verifier("finished successfully"), /outside allowed path|CalledProcessError/);
    assert.throws(() => verifier(replay.artifact.diff.replaceAll("create_lead.sql", "private.sql")), /outside allowed path/);
    assert.throws(() => verifier(replay.artifact.diff.replace("WHERE NOT EXISTS", "WHERE EXISTS")), /retry did not preserve/);
    await assert.rejects(submit("first", first, change), /stale or invalid worker lease/);
    assert.equal((await submit("replacement", second, change)).status, "VERIFYING");
    const history = (await db.query("SELECT lease_generation,status FROM " + schema + "agent_runs ORDER BY lease_generation")).rows;
    assert.deepEqual(history.map(row => row.status), ["LEASE_EXPIRED", "SUBMITTED_FOR_VERIFICATION"]);
    console.log(JSON.stringify({environment: "local synthetic", provider: "pinned upstream faux replay",
        upstream_sha: "e311d6495124cf0bdc629c813fc97a39a9a3054d", real_model_job: false,
        interrupted, restarted: replay.id, history, goal_state: "VERIFYING", current_lease_required: true,
        unverifiable_result_rejected: true, out_of_scope_rejected: true, ineffective_patch_rejected: true,
        elapsed_seconds: Math.round((Date.now() - started)/1000), ...change}, null, 2));
} finally {
    if (db && !db.closed) await db.close();
    await rm(root, {recursive: true, force: true});
}
