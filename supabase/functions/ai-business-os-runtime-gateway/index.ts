import postgres from "npm:postgres@3.4.5";

const EXPECTED_TOKEN_HASH = "83335312c84f0b1d9af19edf7fefb3d8410e2f39b0caf64759a43a4388172b79";

const dbUrl = Deno.env.get("SUPABASE_DB_URL");
if (!dbUrl) throw new Error("SUPABASE_DB_URL is unavailable");
const sql = postgres(dbUrl, { prepare: false, max: 1, idle_timeout: 20 });

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function requireString(value: unknown, name: string): string {
  const text = String(value ?? "").trim();
  if (!text) throw new Error(name + " is required");
  return text;
}

async function authenticated(req: Request): Promise<boolean> {
  const supplied = req.headers.get("X-AIBOS-Runtime-Token") ?? "";
  if (!supplied) return false;
  return (await sha256Hex(supplied)) === EXPECTED_TOKEN_HASH;
}

async function health() {
  const rows = await sql`select ai_business_os_prod.schema_fingerprint_v1() as schema_fingerprint`;
  if (rows.length !== 1) throw new Error("schema fingerprint query returned unexpected row count");
  return { schema_fingerprint: rows[0].schema_fingerprint };
}

async function portfolioView() {
  const [fingerprint, businesses, snapshots, approvals] = await Promise.all([
    sql`select ai_business_os_prod.schema_fingerprint_v1() as schema_fingerprint`,
    sql`select id, slug, name from ai_business_os_prod.businesses order by slug`,
    sql`select snapshot_key, snapshot_hash, payload, generated_at from ai_business_os_prod.command_center_snapshots order by generated_at desc limit 1`,
    sql`select id, request_key, agent_id, action_key, action_class, title, intent_hash, predicted_risk, expected_money_cents, status, created_at, expires_at from ai_business_os_prod.approval_inbox where status='PENDING' order by created_at`,
  ]);
  return {
    schema_fingerprint: fingerprint[0]?.schema_fingerprint ?? null,
    businesses,
    command_center: snapshots[0] ?? null,
    pending_approvals: approvals,
  };
}

async function planningInputs() {
  const [agents, initiatives, gaps, goals] = await Promise.all([
    sql`select agent_id, role_key, display_name, mode, status from ai_business_os_prod.agents where status='ACTIVE' order by role_key`,
    sql`select id, initiative_key, name, business_id, product_id, owner_agent_id, status from ai_business_os_prod.portfolio_initiatives where status='ACTIVE' order by initiative_key`,
    sql`select id, initiative_id, metric_key, gap_type, priority, recommended_source_type, rationale, resolved_at, created_at from ai_business_os_prod.portfolio_data_gaps where resolved_at is null order by priority desc, created_at asc, metric_key asc`,
    sql`select id, agent_id, goal_type, title, status, priority, constraints, evidence_requirements, created_at, updated_at from ai_business_os_prod.agent_goals where status in ('ACTIVE','PENDING') order by priority desc, created_at asc`,
  ]);
  return { agents, initiatives, data_gaps: gaps, open_goals: goals };
}

async function approvalLookup(payload: Record<string, unknown>) {
  const requestKey = requireString(payload.request_key, "request_key");
  const rows = await sql`select request_key, agent_id, action_key, action_class, intent_hash, status, expires_at from ai_business_os_prod.approval_inbox where request_key=${requestKey}`;
  if (rows.length > 1) throw new Error("approval request is non-unique");
  return { approval: rows[0] ?? null };
}

async function activateGoal(payload: Record<string, unknown>) {
  const agentId = requireString(payload.target_agent_id, "target_agent_id");
  const goalType = requireString(payload.goal_type, "goal_type");
  const objective = requireString(payload.objective, "objective");
  const priority = Number(payload.priority);
  if (!Number.isInteger(priority) || priority < 0 || priority > 100) throw new Error("priority must be an integer from 0 to 100");
  const constraints = payload.constraints;
  const evidence = payload.evidence_requirements;
  if (!constraints || typeof constraints !== "object" || Array.isArray(constraints)) throw new Error("constraints must be an object");
  if (!Array.isArray(evidence) || !evidence.every((x) => typeof x === "string")) throw new Error("evidence_requirements must be a string array");

  return await sql.begin(async (tx) => {
    const agents = await tx`select agent_id from ai_business_os_prod.agents where agent_id=${agentId} and status='ACTIVE' for share`;
    if (agents.length !== 1) throw new Error("target agent is not active");
    const rows = await tx`
      insert into ai_business_os_prod.agent_goals(
        agent_id, goal_type, title, status, priority, constraints,
        evidence_requirements, created_at, updated_at
      ) values (
        ${agentId}, ${goalType}, ${objective}, 'PENDING', ${priority},
        ${JSON.stringify(constraints)}::jsonb, ${JSON.stringify(evidence)}::jsonb,
        now(), now()
      )
      returning id, agent_id, goal_type, title, status, priority, constraints, evidence_requirements
    `;
    return { goal: rows[0] };
  });
}

async function decideApproval(payload: Record<string, unknown>) {
  const requestKey = requireString(payload.request_key, "request_key");
  const intentHash = requireString(payload.intent_hash, "intent_hash");
  const decision = requireString(payload.decision, "decision").toUpperCase();
  const human = requireString(payload.human_principal, "human_principal");
  const reason = requireString(payload.reason, "reason");
  if (decision !== "APPROVE" && decision !== "REJECT") throw new Error("decision must be APPROVE or REJECT");

  return await sql.begin(async (tx) => {
    const rows = await tx`select request_key, intent_hash, status from ai_business_os_prod.approval_inbox where request_key=${requestKey} for update`;
    if (rows.length !== 1) throw new Error("approval request is missing or non-unique");
    if (rows[0].status !== "PENDING") throw new Error("approval request is not PENDING");
    if (rows[0].intent_hash !== intentHash) throw new Error("approval intent hash mismatch");
    const decided = await tx`select * from ai_business_os_prod.approval_decide(${requestKey}, ${decision}, ${human}, ${reason})`;
    if (decided.length !== 1) throw new Error("approval decision returned unexpected row count");
    return { receipt: decided[0] };
  });
}

Deno.serve(async (req: Request) => {
  try {
    if (req.method !== "POST") return json({ ok: false, error: "method_not_allowed" }, 405);
    if (!(await authenticated(req))) return json({ ok: false, error: "unauthorized" }, 401);
    const body = await req.json();
    if (!body || typeof body !== "object") throw new Error("request body must be an object");
    const action = requireString((body as any).action, "action");
    const payload = ((body as any).payload ?? {}) as Record<string, unknown>;

    let data: unknown;
    switch (action) {
      case "health": data = await health(); break;
      case "portfolio_view": data = await portfolioView(); break;
      case "planning_inputs": data = await planningInputs(); break;
      case "approval_lookup": data = await approvalLookup(payload); break;
      case "activate_goal": data = await activateGoal(payload); break;
      case "decide_approval": data = await decideApproval(payload); break;
      default: return json({ ok: false, error: "unsupported_action" }, 400);
    }
    return json({ ok: true, data });
  } catch (error) {
    console.error(error);
    return json({ ok: false, error: String((error as Error)?.message ?? error) }, 400);
  }
});
