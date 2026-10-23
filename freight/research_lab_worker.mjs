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
  permitplate: ["NYC DOB building permits", "DOB NOW approved permits", "NYC DOB permit issuance"],
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

const PERMITPLATE_KNOWN_NON_DOB_DATASET_IDS = new Set(["43nn-pn8j", "pitm-atqc", "qcdj-rwhu", "fpeh-f7ci"]);

export function permitplateCandidateInScope(url) {
  const path = new URL(url).pathname.toLowerCase().replace(/\/$/, "");
  return !/(restaurant|inspection|yelp|food[-_ ]?safety|dine[-_ ]?safe)/i.test(path)
    && !PERMITPLATE_KNOWN_NON_DOB_DATASET_IDS.has(path.split("/").pop());
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
      const title = v && v.resource && v.resource.name;
      if (typeof id === "string" && /^[a-z0-9]{4}-[a-z0-9]{4}$/.test(id)
          && typeof title === "string"
          && /\b(dob|building|construction)\b/i.test(title)
          && /\b(permits?|filings?|applications?|certificates?)\b/i.test(title)
          && !/\b(restaurant|inspection)\b/i.test(title)) {
        out.push("https://data.cityofnewyork.us/d/" + id);
      }
    }
  } else {
    throw Error("UNSUPPORTED_PROVIDER");
  }
  return [...new Set(out)].sort();
}

export function feedSpecs(engine, whenMs = 0) {
  if (!ENGINES.includes(engine)) throw Error("INVALID_ENGINE");
  if (!Number.isFinite(whenMs) || whenMs < 0) throw Error("INVALID_SCHEDULE_TIME");
  // One lane per 20 minutes; cycle public search terms and safe result pages
  // without increasing provider request volume or fetching original documents.
  const lap = Math.floor(whenMs / (300000 * ENGINES.length));
  const page = [1, 1, 2, 1, 3][lap % 5];
  // One extra newest-first GitHub view per five runs; total request count stays fixed.
  const newest = lap % 5 === 3;
  // Three search topics x four distinct page/sort plans = 12 bounded views.
  const offset = lap % 3;
  const githubOptions = (q) => ({q: q + " in:name,description", per_page:15, page,
    ...(newest ? {sort:"updated", order:"desc"} : {})});
  const query = QUERIES[engine];
  const [q1, q2, q3] = [query[offset], query[(offset + 1) % 3], query[(offset + 2) % 3]];
  const feeds = [
    {provider: "github", name: "github-primary", url: queryUrl("https://api.github.com/search/repositories", githubOptions(q1))},
    {provider: "github", name: "github-secondary", url: queryUrl("https://api.github.com/search/repositories", githubOptions(q2))},
    {provider: "zenodo", name: "zenodo-archive", url: queryUrl("https://zenodo.org/api/records", {q: q3, size: 15, page})},
  ];
  if (engine === "permitplate") {
    feeds.push({provider: "socrata", name: "nyc-official-catalog",
      url: queryUrl("https://api.us.socrata.com/api/catalog/v1",
        {domains: "data.cityofnewyork.us", search_context: "data.cityofnewyork.us", q: "NYC DOB building permit", limit: 15})});
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
  // Bound *bytes while streaming*, not UTF-16 string length after an
  // unbounded .text() read. Never retain oversized provider responses.
  const reader = response.body?.getReader?.();
  if (!reader) throw Error("RESPONSE_STREAM_REQUIRED");
  let size = 0;
  let finished = false;
  const parts = [];
  try {
    for (;;) {
      const part = await reader.read();
      if (part.done) { finished = true; break; }
      if (!(part.value instanceof Uint8Array)) throw Error("RESPONSE_STREAM_INVALID");
      size += part.value.byteLength;
      if (size > MAX_API_BYTES) throw Error("RESPONSE_LIMIT");
      parts.push(part.value);
    }
  } finally {
    if (!finished) await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
  if (!size) throw Error("EMPTY_RESPONSE");
  const bodyBytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) { bodyBytes.set(part, offset); offset += part.byteLength; }
  const payload = new TextDecoder("utf-8", {fatal:true}).decode(bodyBytes);
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

export function providerErrorCode(error) {
  // Fixed telemetry enums only: never persist untrusted exception text,
  // credentials, user identifiers, provider URLs, or arbitrary headers.
  const message = typeof error?.message === "string" ? error.message : "";
  const name = typeof error?.name === "string" ? error.name : "";
  if (/^HTTP_(400|401|403|404|408|429|500|502|503|504)$/.test(message)) return message;
  if (["REDIRECT_BLOCKED", "RESPONSE_LIMIT", "CONTENT_TYPE", "INVALID_ITEMS",
       "INVALID_RESPONSE", "RESPONSE_STREAM_REQUIRED", "RESPONSE_STREAM_INVALID",
       "EMPTY_RESPONSE", "UNSUPPORTED_PROVIDER"].includes(message)) return message;
  if (name === "TimeoutError" || name === "AbortError") return "TIMEOUT";
  if (name === "SyntaxError") return "JSON_INVALID";
  if (name === "TypeError") return "FETCH_TYPEERROR";
  return "SOURCE_UNAVAILABLE";
}

async function sha256url(url) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(url));
  return Array.from(new Uint8Array(bytes), x => x.toString(16).padStart(2, "0")).join("");
}
/**
 * Store a maximum of 24 canonical public pointers per Cron invocation.
 * D1 batch() is transactional: source links and engine associations commit
 * together or neither commits. Two SQL statements replace up to 48 RPCs.
 */
export async function persistSourceWindow(db, lane, candidates, now) {
  if (!ENGINES.includes(lane)) throw Error("INVALID_ENGINE");
  const window = selectCandidateWindow(candidates, now);
  if (!window.length) return {newSources: 0, attempted: 0};
  const ids = await Promise.all(window.map(sha256url));
  const day = new Date(now).toISOString().slice(0, 10);
  const values = window.map(() => "(?,?,?,'UNVERIFIED_RIGHTS_HOLD','UNVERIFIED_TRUTH_HOLD')").join(",");
  const memberships = window.map(() => "(?,?)").join(",");
  const first = [];
  const second = [];
  for (let i = 0; i < window.length; i++) {
    first.push(ids[i], window[i], day);
    second.push(ids[i], lane);
  }
  const src = db.prepare(
    "INSERT OR IGNORE INTO sources(id,url,first_seen,rights_state,truth_state) VALUES " + values
  ).bind(...first);
  const associate = db.prepare(
    "INSERT OR IGNORE INTO source_engines(source_id,lane) VALUES " + memberships
  ).bind(...second);
  const results = await db.batch([src, associate]);
  if (!Array.isArray(results) || results.length !== 2 ||
      !Number.isInteger(results[0]?.meta?.changes) ||
      results[0].meta.changes < 0 || results[0].meta.changes > window.length ||
      !Number.isInteger(results[1]?.meta?.changes)) {
    throw Error("INVALID_STORAGE_RECEIPT");
  }
  return {newSources: results[0].meta.changes, attempted: window.length};
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
  let githubRateLimited = false;
  for (const spec of feedSpecs(lane, now)) {
    if (spec.provider === "github" && githubRateLimited) {
      errors.push(spec.name + ":SKIPPED_RATE_LIMIT");
      continue;
    }
    try {
      for (const url of await fetchCatalog(spec)) candidates.add(url);
      successfulFeeds++;
    } catch (error) {
      const code = providerErrorCode(error);
      errors.push(spec.name + ":" + code);
      if (spec.provider === "github" && code === "HTTP_429") githubRateLimited = true;
    }
  }
  let added = 0;
  let storageFailed = false;
  if (successfulFeeds > 0) {
    const scopedCandidates = lane === "permitplate"
      ? [...candidates].filter(permitplateCandidateInScope) : candidates;
    try {
      const written = await persistSourceWindow(env.RESEARCH_DB, lane, scopedCandidates, now);
      added = written.newSources;
    } catch {
      // The D1 batch rolls back all candidate writes, and the failure is
      // recorded as such, rather than falsely promoting a healthy scan.
      storageFailed = true;
      errors.push("storage:STORAGE_WRITE_FAILED");
    }
  }
  const status = storageFailed || !successfulFeeds ? "FAILED" : (errors.length ? "DEGRADED" : "OK");
  const finished = Date.now();
  await env.RESEARCH_DB.prepare(
    "UPDATE runs SET status=?,finished_ms=?,new_sources=?,feed_errors=? WHERE run_key=?"
  ).bind(status, finished, added, JSON.stringify(errors), uniqueRun).run();
  if (status !== "FAILED") {
    await env.RESEARCH_DB.prepare(
      "UPDATE lane_health SET last_success_ms=?,last_status=? WHERE name=?"
    ).bind(finished, status, lane).run();
  } else {
    await env.RESEARCH_DB.prepare(
      "UPDATE lane_health SET last_status=? WHERE name=?"
    ).bind(status, lane).run();
  }
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
      const metrics = await env.RESEARCH_DB.prepare(
        "SELECT lane, COUNT(*) AS runs, SUM(status='OK') AS ok, SUM(status='DEGRADED') AS degraded, SUM(status='FAILED') AS failed, SUM(new_sources) AS new_sources FROM runs WHERE started_ms >= ? GROUP BY lane ORDER BY lane"
      ).bind(Date.now() - 86400000).all();
      const associations = await env.RESEARCH_DB.prepare(
        "SELECT lane, COUNT(*) AS source_pointers FROM source_engines GROUP BY lane ORDER BY lane"
      ).all();
      return json({system:"RETALLY_UNIFIED_RESEARCH",scope:"PUBLIC_METADATA_ONLY",
        total_source_references:total.total, lanes:status.results, recent_runs:runs.results,
        last_24_hours:metrics.results, source_pointers_by_lane:associations.results,
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
