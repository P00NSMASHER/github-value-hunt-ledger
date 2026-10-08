import superjson from "superjson";
import { sql } from "kysely";
import { db } from "../../helpers/db";
import type { JsonValue } from "../../helpers/schema";
import { recoveryHash } from "../../helpers/recoveryHash";
import { requireRecoveryTenant, requireReviewPermission } from "../../helpers/recoveryTenant";
import { schema, OutputType } from "./payment_prepare_POST.schema";

/** M8 staging: PostgreSQL is authoritative for eligibility and conserved allocation. */
export async function handle(request: Request) {
  try {
    const access = await requireRecoveryTenant(request);
    requireReviewPermission(access);
    const input = schema.parse(superjson.parse(await request.text()));
    const orderedIds = [...input.findingIds].sort();
    if (orderedIds.some((id,index) => index>0 && id===orderedIds[index-1])) {
      throw new Error("Duplicate findings cannot be allocated in one instruction");
    }
    const body: JsonValue = {
      schema:1, tenant_id:access.tenantId, payer_id:input.payerId,
      payee_id:input.payeeId, currency:input.currency,
      amount_cents:input.amountCents, purpose:input.purpose.trim(),
      finding_ids:orderedIds, idempotency_key:input.idempotencyKey,
    };
    const instructionHash = recoveryHash(body);
    const result = await sql<{
      instruction_id:string;instruction_hash:string;replayed:boolean;
    }>`SELECT * FROM recovery_prepare_financial_instruction(
        ${access.tenantId}::text,${access.userId}::bigint,
        ${JSON.stringify(body)}::jsonb,${instructionHash}::text
      )`.execute(db);
    const entry = result.rows[0];
    if (!entry || entry.instruction_hash!==instructionHash) {
      throw new Error("Financial allocation reconciliation failed");
    }
    const output: OutputType = {
      instructionId:entry.instruction_id,
      instructionHash:entry.instruction_hash,
      status:"PREPARED",
    };
    return new Response(superjson.stringify(output),{headers:{"Content-Type":"application/json"}});
  } catch(error) {
    const message = error instanceof Error ? error.message : "Financial payment preparation failed";
    return new Response(superjson.stringify({error:message}),{status:400});
  }
}
