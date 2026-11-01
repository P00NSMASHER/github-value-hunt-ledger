import superjson from "superjson";
import { sql } from "kysely";
import { db } from "../../helpers/db";
import { requireRecoveryTenant } from "../../helpers/recoveryTenant";
import { OutputType } from "./dashboard_GET.schema";

function number(value: string | number | bigint | null | undefined): number {
  if (value == null) return 0;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) throw new Error("Money/count exceeds safe integer range");
  return parsed;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((x): x is string => typeof x === "string") : [];
}

export async function handle(request: Request) {
  try {
    const access = await requireRecoveryTenant(request);
    const [records, findingTotalsResult, reviewRowsResult, confirmedResult, currencyTotalsResult] = await Promise.all([
      db.selectFrom("recoveryFreightRecords").select(({ fn }) => [fn.countAll<string>().as("count")]).where("tenantId", "=", access.tenantId).executeTakeFirstOrThrow(),
      sql<{count:string;challengerOnly:string;candidateDifferenceCents:string}>`
        select
          count(*)::bigint as "count",
          count(*) filter (where attribution_state='CHALLENGER_ONLY')::bigint as "challengerOnly",
          coalesce(sum(variance_cents),0)::bigint as "candidateDifferenceCents"
        from recovery_challenge_findings
        where tenant_id=${access.tenantId}
      `.execute(db),
      sql<{
        id:string;
        economicKey:string;
        category:string;
        billedCents:string;
        expectedCents:string;
        varianceCents:string;
        confidencePpm:number;
        attributionState:string;
        blockerCodes:unknown;
        evidence:unknown;
        findingHash:string;
        currency:string;
      }>`
        select
          f.id,
          f.economic_key as "economicKey",
          f.category,
          f.billed_cents::text as "billedCents",
          f.expected_cents::text as "expectedCents",
          f.variance_cents::text as "varianceCents",
          f.confidence_ppm as "confidencePpm",
          f.attribution_state as "attributionState",
          f.blocker_codes as "blockerCodes",
          f.evidence,
          f.finding_hash as "findingHash",
          r.currency as currency
        from recovery_challenge_findings f
        join recovery_freight_records r on r.tenant_id=f.tenant_id and r.record_hash=f.record_hash
        left join lateral (
          select d.decision
          from recovery_review_dispositions d
          where d.tenant_id=f.tenant_id and d.finding_id=f.id
          order by d.created_at desc, d.id desc
          limit 1
        ) latest on true
        where f.tenant_id=${access.tenantId}
          and coalesce(latest.decision,'') not in ('CONFIRM','REJECT')
        order by f.variance_cents desc, f.id
        limit 100
      `.execute(db),
      sql<{count:string}>`
        select count(*)::bigint as "count"
        from (
          select distinct on (finding_id) finding_id, decision
          from recovery_review_dispositions
          where tenant_id=${access.tenantId}
          order by finding_id, created_at desc, id desc
        ) latest
        where decision='CONFIRM'
      `.execute(db),
      sql<{currency:string;candidateCents:string;netNewCents:string}>`
        SELECT r.currency,
          coalesce(sum(f.variance_cents),0)::text AS "candidateCents",
          coalesce(sum(f.net_new_candidate_cents),0)::text AS "netNewCents"
        FROM recovery_challenge_findings f
        JOIN recovery_freight_records r
          ON r.tenant_id=f.tenant_id AND r.record_hash=f.record_hash
        WHERE f.tenant_id=${access.tenantId}
        GROUP BY r.currency ORDER BY r.currency
      `.execute(db),
    ]);
    const findingTotals = findingTotalsResult.rows[0] ?? {count:"0",challengerOnly:"0",candidateDifferenceCents:"0"};
    const currencyTotals = currencyTotalsResult.rows.map(r=>({
      currency:r.currency,
      candidateDifferenceCents:number(r.candidateCents),
      netNewCandidateCents:number(r.netNewCents),
    }));
    const findings = reviewRowsResult.rows;
    const reviewQueue = findings
      .map(x => ({
        id: x.id,
        carrier: "Evidence-linked carrier",
        invoice: x.economicKey.split("|")[0] || x.economicKey,
        category: x.category,
        billedCents: number(x.billedCents),
        expectedCents: number(x.expectedCents),
        varianceCents: number(x.varianceCents),
        confidencePpm: x.confidencePpm,
        attributionState: x.attributionState,
        blockerCodes: strings(x.blockerCodes),
        evidence: strings(x.evidence),
        findingHash: x.findingHash,
        currency:x.currency,
      }));
    const confirmedCount = number(confirmedResult.rows[0]?.count);
    const payload: OutputType = {
      tenant: { id: access.tenantId, name: access.tenantName, role: access.role },
      totals: {
        recordsReviewed: number(records.count),
        findings: number(findingTotals.count),
        challengerOnly: number(findingTotals.challengerOnly),
        // Legacy field only expresses USD. Other currencies remain separately identified.
        candidateDifferenceCents: currencyTotals.find(x=>x.currency==="USD")?.candidateDifferenceCents ?? 0,
        candidateDifferenceCurrency:"USD",
        candidateByCurrency:currencyTotals,
        confirmedCount,
      },
      reviewQueue,
    };
    return new Response(superjson.stringify(payload), { headers: { "Content-Type": "application/json" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Dashboard request failed";
    return new Response(superjson.stringify({ error: message }), { status: 401 });
  }
}
