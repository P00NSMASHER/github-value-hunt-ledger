/**
 * RETALLY Unified Research Lab — independent bounded scheduled scout.
 * Cloudflare Cron is a trigger fallback when GitHub Actions schedules are late.
 * Only public catalog metadata IDs/URLs are persisted. Never collect raw
 * invoices, customer data, credentials, contacts, or financial truth labels.
 *
 * Deploy with its OWN dedicated D1 binding: RESEARCH_DB.
 * No public HTTP mutation routes; only scheduled() writes to storage.
 */
export const ENGINES = Object.freeze(["freightrecovery", "permitplate", "capturebrief", "recoveryos"]);
const QUERIES = Object.freeze({
  freightrecovery: ["freight invoice dataset", "freight overcharge audit", "LTL shipping tariff"],
  permitplate: ["NYC restaurant inspection", "restaurant permit dataset", "New York building license"],
  capturebrief: ["federal solicitation archive", "federal contract dataset", "government contract awards"],
  recoveryos: ["accounts payable dataset", "supplier payment invoices", "public sector vendor spend"],
});
const MAX_NEW = 24;
const MAX_API_BYTES = 1200000;

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store, max-age=0",
      "X-Content-Type-Options": "nosniff",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
function queryUrl(base, params) {
  const url = new URL(base);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));
  return url.toString();
}

export function canonicalCandidates(provider, data) {
  const out = [];
  if (!data || typeof data !== "object" || Array.isArray(data)) throw Error("INVALID_RESPONSE");
  if (provider === "github") {
    if (!Array.isArray(data.items)) throw Error("INVALID_ITEMS");
    for (const v of data.items.slice(0, 15)) {
      const link = v && v.html_url;
      if (typeof link === "string" && /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(link)) out.push(link);
    }
  } else if (provider === "zenodo") {
    const list = data.hits && data.hits.hits;
    if (!Array.isArray(list)) throw Error("INVALID_ITEMS");
    for (const v of list.slice(0, 15)) {
      const id = v && String(v.id);
      if (/^[1-9]\d{0,14}$/.test(id)) out.push("https://zenodo.org/records/" + id);
    }
  } else if (provider === "socrata") {
    if (!Array.isArray(data.results)) throw Error("INVALID_ITEMS");
    for (const v of data.results.slice(0, 15)) {
      const id = v && v.resource && v.resource.id;
      if (typeof id === "string" && /^[a-z0-9]{4}-[a-z0-9]{4}$/.test(id)) {
        out.push("https://data.cityofnewyork.us/d/" + id);
      }
    }
  } else {
    throw Error("UNSUPPORTED_PROVIDER");
  }
  return [...new Set(out)].sort();
}

export function feedSpecs(engine) {
  if (!ENGINES.includes(engine)) throw Error("INVALID_ENGINE");
  const [q1, q2, q3] = QUERIES[engine];
  const feeds = [
    {provider: "github", name: "github-primary", url: queryUrl("https://api.github.com/search/repositories", {q: q1 + " in:name,description", per_page: 15})},
    {provider: "github", name: "github-secondary", url: queryUrl("https://api.github.com/search/repositories", {q: q2 + " in:name,description", per_page: 15})},
    {provider: "zenodo", name: "zenodo-archive", url: queryUrl("https://zenodo.org/api/records", {q: q3, size: 15})},
  ];
  if (engine === "permitplate") {
    feeds.push({provider: "socrata", name: "nyc-official-catalog",
      url: queryUrl("https://api.us.socrata.com/api/catalog/v1",
        {domains: "data.cityofnewyork.us", search_context: "data.cityofnewyork.us", q: "restaurant permit", limit: 15})});
  }
  return feeds;
}
export async function fetchCatalog(spec) {
  const response = await fetch(spec.url, {
    method: "GET",
    redirect: "manual",
    headers: {"Accept": "application/json", "User-Agent": "RETALLY-UnifiedResearch/1.1 public catalog metadata only"},
    signal: AbortSignal.timeout(9000),
    cf: {cacheTtl: 0},
  });
  // Cloudflare's fetch runtime rejects redirect:'error'. Manual mode never
  // follows the Location header, and every redirect response fails closed.
  if (response.type === "opaqueredirect" || response.status === 0 ||
      (response.status >= 300 && response.status < 400)) {
    throw Error("REDIRECT_BLOCKED");
  }
  if (!response.ok) throw Error("HTTP_" + response.status);
  const type = (response.headers.get("content-type") || "").split(";")[0].toLowerCase();
  if (type !== "application/json" && type !== "application/vnd.github+json") throw Error("CONTENT_TYPE");
  const bytes = Number(response.headers.get("content-length") || 0);
  if (bytes > MAX_API_BYTES) throw Error("RESPONSE_LIMIT");
  const payload = await response.text();
  if (payload.length > MAX_API_BYTES) throw Error("RESPONSE_LIMIT");
  return canonicalCandidates(spec.provider, JSON.parse(payload));
}
/**
 * Rotate bounded discovery windows instead of permanently replaying the first
 * 24 alphabetically sorted links. A stable 4-lane cycle advances a window
 * every 20 minutes, eventually covering every candidate in a stable feed.
 */
export function selectCandidateWindow(candidates, whenMs) {
  if (!Number.isFinite(whenMs) || whenMs < 0) throw Error("INVALID_SCHEDULE_TIME");
  const unique = [...new Set(candidates)].sort();
  if (unique.length === 0) return [];
  const windowCount = Math.ceil(unique.length / MAX_NEW);
  const cycle = Math.floor(whenMs / (300000 * ENGINES.length));
  const window = cycle % windowCount;
  return unique.slice(window * MAX_NEW, (window + 1) * MAX_NEW);
}

async function sha256url(url) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(url));
  return Array.from(new Uint8Array(bytes), x => x.toString(16).padStart(2, "0")).join("");
}
async function chooseLane(db) {
  const row = await db.prepare("SELECT name FROM lane_health ORDER BY last_attempt_ms ASC, name ASC LIMIT 1").first();
  if (!row || !ENGINES.includes(row.name)) throw Error("UNINITIALIZED_DATABASE");
  return row.name;
}

export async function cycle(env, whenMs) {
  if (!env.RESEARCH_DB) throw Error("RESEARCH_D1_MISSING");
  const now = Number.isFinite(whenMs) ? whenMs : Date.now();
  const lane = await chooseLane(env.RESEARCH_DB);
  const uniqueRun = String(Math.floor(now / 300000)) + ":" + lane;
  const claimed = await env.RESEARCH_DB.prepare(
    "INSERT OR IGNORE INTO runs (run_key,lane,started_ms,status,new_sources,feed_errors) VALUES (?,?,?,'RUNNING',0,'[]')"
  ).bind(uniqueRun, lane, now).run();
  if (claimed.meta.changes === 0) return {state: "DUPLICATE", lane};
  await env.RESEARCH_DB.prepare("UPDATE lane_health SET last_attempt_ms=? WHERE name=?").bind(now, lane).run();

  const candidates = new Set();
  const errors = [];
  let successfulFeeds = 0;
  for (const spec of feedSpecs(lane)) {
    try {
      for (const url of await fetchCatalog(spec)) candidates.add(url);
      successfulFeeds++;
    } catch (error) {
      // Never log untrusted response contents, URLs or tokens.
      const marker = String(error && error.message || "UNAVAILABLE");
      const kind = String(error && error.name || "Error");
      // For debugging a failing cron, keep the safe exception category and
      // bounded reason. No raw provider documents or secrets are ever logged.
      const safeReason = marker.slice(0, 100)
        .replace(/https?:\/\/[^\s]+/g, "[public-endpoint]")
        .replace(/(?:api_?key|token|secret|password)\s*[=:]\s*[^\s,;]*/gi, "[REDACTED]")
        .replace(/[^A-Za-z0-9 _.,:()\/-]/g, "");
      const code = /^(HTTP_\d{3}|CONTENT_TYPE|RESPONSE_LIMIT|INVALID_ITEMS|INVALID_RESPONSE)$/.test(marker)
        ? marker : (kind === "TimeoutError" || kind === "AbortError" ? "TIMEOUT"
          : kind === "TypeError" ? "FETCH_TYPEERROR"
          : kind === "SyntaxError" ? "JSON_INVALID" : "SOURCE_UNAVAILABLE");
      errors.push(spec.name + ":" + code + (safeReason ? ":" + safeReason : ""));
    }
  }
  let added = 0;
  if (successfulFeeds > 0) {
    const today = new Date(now).toISOString().slice(0,10);
    for (const url of selectCandidateWindow(candidates, now)) {
      const id = await sha256url(url);
      const result = await env.RESEARCH_DB.prepare(
        "INSERT OR IGNORE INTO sources(id,url,first_seen,rights_state,truth_state) VALUES(?,?,?,'UNVERIFIED_RIGHTS_HOLD','UNVERIFIED_TRUTH_HOLD')"
      ).bind(id, url, today).run();
      if (result.meta.changes > 0) added++;
      await env.RESEARCH_DB.prepare(
        "INSERT OR IGNORE INTO source_engines(source_id,lane) VALUES(?,?)"
      ).bind(id, lane).run();
    }
  }
  const status = successfulFeeds ? (errors.length ? "DEGRADED" : "OK") : "FAILED";
  await env.RESEARCH_DB.prepare(
    "UPDATE runs SET status=?,finished_ms=?,new_sources=?,feed_errors=? WHERE run_key=?"
  ).bind(status, Date.now(), added, JSON.stringify(errors), uniqueRun).run();
  if (successfulFeeds) await env.RESEARCH_DB.prepare(
    "UPDATE lane_health SET last_success_ms=?,last_status=? WHERE name=?"
  ).bind(Date.now(),status,lane).run();
  else await env.RESEARCH_DB.prepare(
    "UPDATE lane_health SET last_status=? WHERE name=?"
  ).bind(status,lane).run();
  // No customer actions, raw files, billing, marketing or private connectors.
  return {state: status, lane, discovered: candidates.size, added, provider_errors: errors.length};
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(cycle(env, controller.scheduledTime).then(
      result => console.log("research_cron", JSON.stringify(result)),
      error => console.error("research_cron_failed", String(error && error.message || "unknown"))
    ));
  },
  async fetch(request, env) {
    if (request.method !== "GET") return json({error:"READ_ONLY"}, 405);
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      const status = await env.RESEARCH_DB.prepare(
        "SELECT name,last_attempt_ms,last_success_ms,last_status FROM lane_health ORDER BY name"
      ).all();
      const total = await env.RESEARCH_DB.prepare("SELECT COUNT(*) AS total FROM sources").first();
      const runs = await env.RESEARCH_DB.prepare(
        "SELECT run_key,lane,status,new_sources,feed_errors,started_ms FROM runs ORDER BY started_ms DESC LIMIT 8"
      ).all();
      return json({system:"RETALLY_UNIFIED_RESEARCH",scope:"PUBLIC_METADATA_ONLY",
        total_source_references:total.total, lanes:status.results, recent_runs:runs.results,
        commercial_approval:false, independent_truth_verified:false});
    }
    if (url.pathname === "/feed") {
      const lane = url.searchParams.get("engine");
      if (!ENGINES.includes(lane)) return json({error:"INVALID_ENGINE"},400);
      const lim = Math.min(100,Math.max(1,Number.parseInt(url.searchParams.get("limit") || "50",10)||50));
      const rows = await env.RESEARCH_DB.prepare(
        "SELECT s.url,s.first_seen FROM sources s INNER JOIN source_engines e ON e.source_id=s.id WHERE e.lane=? ORDER BY s.rowid DESC LIMIT ?"
      ).bind(lane,lim).all();
      return json({engine:lane,scope:"PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",sources:rows.results});
    }
    return json({error:"NOT_FOUND"},404);
  },
};
