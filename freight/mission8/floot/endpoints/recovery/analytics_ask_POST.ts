import { flootAi, FlootAiOutOfCreditsError, FlootAiRateLimitError } from "@floot/ai";
import superjson from "superjson";
import { sql } from "kysely";
import { db } from "../../helpers/db";
import { requireRecoveryTenant } from "../../helpers/recoveryTenant";
import { schema, OutputType, AnalyticsRow } from "./analytics_ask_POST.schema";

const INTENTS = {
  overview: "Overall freight audit/recovery status or a general summary.",
  spend_by_mode: "Billed freight spend grouped by transportation mode.",
  records_by_mode: "Freight record or invoice/shipment counts grouped by mode.",
  candidate_by_category: "Candidate overcharge variance dollars grouped by finding category.",
  net_new_by_category: "Challenger-only net-new candidate dollars grouped by finding category.",
  findings_by_attribution: "Finding counts grouped by attribution state such as challenger-only or incumbent-known.",
  confirmed_findings: "Count of findings whose latest human review disposition is CONFIRM.",
  payment_pipeline: "Payment instruction counts and amounts by current payment lifecycle state.",
  settled_payments_by_provider: "Currently settled payment amounts grouped by payment provider.",
} as const;

type Intent = keyof typeof INTENTS;

function number(value: string | number | bigint | null | undefined): number {
  if (value == null) return 0;
  const n = Number(value);
  if (!Number.isSafeInteger(n)) throw new Error("Analytics value exceeds safe integer range");
  return n;
}

function money(cents: number, currency?: string): string {
  if (!currency) return String(cents) + " minor units (currency unspecified)";
  return new Intl.NumberFormat("en-US",{style:"currency",currency}).format(cents/100);
}
function summarize(intent: Intent, rows: AnalyticsRow[]): string {
  if (!rows.length) return "No tenant-scoped data matches that analytics view yet.";
  const format=(r:AnalyticsRow)=>r.valueType==="cents"
    ? money(r.value,r.currency) : r.value.toLocaleString("en-US");
  if (intent==="overview") return rows.map(r=>r.label+": "+format(r)).join(" · ");
  return "Top result: "+rows[0].label+" — "+format(rows[0])+".";
}

async function executeIntent(intent: Intent, tenantId: string): Promise<AnalyticsRow[]> {
  if (intent==="spend_by_mode" || intent==="records_by_mode") {
    const rows = await db.selectFrom("recoveryFreightRecords")
      .select(({fn})=>["mode","currency",fn.countAll<string>().as("recordCount"),fn.sum<string>("billedTotalCents").as("billedCents")])
      .where("tenantId","=",tenantId).groupBy(["mode","currency"]).execute();
    return rows.map(r=>({label:r.mode+" ("+r.currency+")",
      currency:r.currency,value:intent==="spend_by_mode"?number(r.billedCents):number(r.recordCount),
      valueType:intent==="spend_by_mode"?"cents" as const:"count" as const})).sort((a,b)=>b.value-a.value);
  }
  if (intent==="candidate_by_category" || intent==="net_new_by_category") {
    const result=await sql<{category:string;currency:string;candidate:string;netNew:string}>`
      SELECT f.category,r.currency,coalesce(sum(f.variance_cents),0)::text AS candidate,
        coalesce(sum(f.net_new_candidate_cents),0)::text AS "netNew"
      FROM recovery_challenge_findings f
      JOIN recovery_freight_records r ON r.tenant_id=f.tenant_id AND r.record_hash=f.record_hash
      WHERE f.tenant_id=${tenantId} GROUP BY f.category,r.currency
    `.execute(db);
    return result.rows.map(r=>({label:r.category+" ("+r.currency+")",currency:r.currency,
       value:intent==="candidate_by_category"?number(r.candidate):number(r.netNew),
       valueType:"cents" as const})).sort((a,b)=>b.value-a.value);
  }

  if (intent === "findings_by_attribution") {
    const rows = await db.selectFrom("recoveryChallengeFindings")
      .select(({fn}) => ["attributionState",fn.countAll<string>().as("count")])
      .where("tenantId","=",tenantId)
      .groupBy("attributionState")
      .execute();
    return rows.map(r => ({label:r.attributionState,value:number(r.count),valueType:"count" as const})).sort((a,b)=>b.value-a.value);
  }

  if (intent === "confirmed_findings") {
    const result = await sql<{count:string}>`
      select count(*)::bigint as "count"
      from (
        select distinct on (finding_id) finding_id, decision
        from recovery_review_dispositions
        where tenant_id=${tenantId}
        order by finding_id, created_at desc, id desc
      ) latest
      where decision='CONFIRM'
    `.execute(db);
    return [{label:"confirmed findings",value:number(result.rows[0]?.count),valueType:"count"}];
  }

  if (intent === "payment_pipeline" || intent === "settled_payments_by_provider") {
    if (intent === "payment_pipeline") {
      const result = await sql<{label:string;value:string;currency:string}>`
        select
          coalesce(
            latest.state,
            case when auth.instruction_id is not null then 'AUTHORIZED' else 'PREPARED' end
          ) as label,
          i.currency AS currency, sum(i.amount_cents)::bigint as value
        from recovery_payment_instructions i
        left join recovery_payment_authorizations auth
          on auth.tenant_id=i.tenant_id and auth.instruction_id=i.id
        left join lateral (
          select e.state,e.provider
          from recovery_payment_events e
          where e.tenant_id=i.tenant_id and e.instruction_id=i.id
          order by e.occurred_at desc,e.created_at desc,e.id desc
          limit 1
        ) latest on true
        where i.tenant_id=${tenantId}
        group by 1,i.currency
        order by sum(i.amount_cents) desc
      `.execute(db);
      return result.rows.map(row=>({label:row.label+" ("+row.currency+")",currency:row.currency,value:number(row.value),valueType:"cents" as const}));
    }
    const result = await sql<{label:string;value:string;currency:string}>`
      select coalesce(latest.provider,'unknown provider') as label,
             i.currency AS currency,sum(i.amount_cents)::bigint as value
      from recovery_payment_instructions i
      join lateral (
        select e.state,e.provider
        from recovery_payment_events e
        where e.tenant_id=i.tenant_id and e.instruction_id=i.id
        order by e.occurred_at desc,e.created_at desc,e.id desc
        limit 1
      ) latest on true
      where i.tenant_id=${tenantId} and latest.state='SETTLED'
      group by 1,i.currency
      order by sum(i.amount_cents) desc
    `.execute(db);
    return result.rows.map(row=>({label:"Provider-reported SETTLED — "+row.label+" ("+row.currency+")",currency:row.currency,value:number(row.value),valueType:"cents" as const}));
  }

  const records=await db.selectFrom("recoveryFreightRecords")
    .select(({fn})=>fn.countAll<string>().as("count")).where("tenantId","=",tenantId).executeTakeFirstOrThrow();
  const findings=await db.selectFrom("recoveryChallengeFindings")
    .select(({fn})=>fn.countAll<string>().as("count")).where("tenantId","=",tenantId).executeTakeFirstOrThrow();
  const challenger=await db.selectFrom("recoveryChallengeFindings")
    .select(({fn})=>fn.countAll<string>().as("count")).where("tenantId","=",tenantId)
    .where("attributionState","=","CHALLENGER_ONLY").executeTakeFirstOrThrow();
  const monies=await sql<{currency:string;candidate:string;netNew:string}>`
    SELECT r.currency,coalesce(sum(f.variance_cents),0)::text AS candidate,
      coalesce(sum(f.net_new_candidate_cents),0)::text AS "netNew"
    FROM recovery_challenge_findings f
    JOIN recovery_freight_records r ON r.tenant_id=f.tenant_id AND r.record_hash=f.record_hash
    WHERE f.tenant_id=${tenantId} GROUP BY r.currency
  `.execute(db);
  const output:AnalyticsRow[]=[
    {label:"records",value:number(records.count),valueType:"count"},
    {label:"findings",value:number(findings.count),valueType:"count"},
    {label:"challenger-only",value:number(challenger.count),valueType:"count"}
  ];
  for(const r of monies.rows){
    output.push({label:"candidate variance ("+r.currency+")",currency:r.currency,value:number(r.candidate),valueType:"cents"});
    output.push({label:"net-new candidate ("+r.currency+")",currency:r.currency,value:number(r.netNew),valueType:"cents"});
  }
  return output;
}


export async function handle(request: Request) {
  try {
    const access = await requireRecoveryTenant(request);
    const input = schema.parse(superjson.parse(await request.text()));
    const direct=(Object.keys(INTENTS) as Intent[]).find(k=>k===input.question.trim()) ?? null;
    const result = direct ? null : await flootAi.evaluate({
      model:"jev-latest",
      state:{question:input.question},
      questions:{
        intent:{
          type:"choice",
          instructions:"Choose the single RecoveryOS analytics view that best answers the question field in state. Do not infer financial facts; only route the question.",
          criteria:INTENTS,
        },
      },
    });
    const intent = direct ?? (result!.answers.intent.choice as Intent);
    const confidence = direct ? 1 : result!.answers.intent.confidence;
    if (confidence < 0.45) {
      return new Response(superjson.stringify({error:"The analytics question is ambiguous. Ask about spend, records, candidate variance, net-new value, attribution, confirmed findings, or payments."}),{status:400});
    }
    const rows = await executeIntent(intent,access.tenantId);
    const output: OutputType = {
      intent,
      confidence,
      answer:summarize(intent,rows),
      rows,
      creditsConsumed:result?.flootCredits.consumed ?? 0,
    };
    return new Response(superjson.stringify(output),{headers:{"Content-Type":"application/json"}});
  } catch (error) {
    if (error instanceof FlootAiOutOfCreditsError) {
      return new Response(superjson.stringify({error:"AI analytics are temporarily unavailable. Please contact the app owner.",code:"OUT_OF_CREDITS"}),{status:503});
    }
    if (error instanceof FlootAiRateLimitError) {
      return new Response(superjson.stringify({error:"AI analytics are temporarily rate limited. Try again in about a minute.",code:"RATE_LIMITED"}),{status:429});
    }
    const message = error instanceof Error ? error.message : "Analytics request failed";
    return new Response(superjson.stringify({error:message}),{status:400});
  }
}
