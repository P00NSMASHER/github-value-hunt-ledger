import superjson from "superjson";
import { db } from "../../helpers/db";
import { requireRecoveryTenant } from "../../helpers/recoveryTenant";
import { NotAuthenticatedError } from "../../helpers/getSetServerSession";
import { OutputType, PaymentRow } from "./payments_GET.schema";

function number(value: string | number | bigint): number {
  const n = Number(value);
  if (!Number.isSafeInteger(n)) throw new Error("Unsafe payment amount");
  return n;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((x):x is string => typeof x === "string") : [];
}

export async function handle(request: Request) {
  try {
    const access = await requireRecoveryTenant(request);
    const instructions = await db.selectFrom("recoveryPaymentInstructions")
      .selectAll()
      .where("tenantId","=",access.tenantId)
      .orderBy("createdAt","desc")
      .limit(250)
      .execute();
    const ids = instructions.map(x=>x.id);
    const [authorizations, events] = ids.length ? await Promise.all([
      db.selectFrom("recoveryPaymentAuthorizations")
        .select("instructionId")
        .where("tenantId","=",access.tenantId)
        .where("instructionId","in",ids)
        .execute(),
      db.selectFrom("recoveryPaymentEvents")
        .select(["instructionId","state","provider","providerReference","occurredAt","createdAt"])
        .where("tenantId","=",access.tenantId)
        .where("instructionId","in",ids)
        .orderBy("occurredAt","asc")
        .orderBy("createdAt","asc")
        .execute(),
    ]) : [[],[]];
    const authorized = new Set(authorizations.map(x=>x.instructionId));
    const latest = new Map<string,{state:string;provider:string|null;providerReference:string|null}>();
    for (const event of events) latest.set(event.instructionId,{state:event.state,provider:event.provider,providerReference:event.providerReference});
    const payments: PaymentRow[] = instructions.map(instruction => {
      const event = latest.get(instruction.id);
      return {
        id:instruction.id,
        payerId:instruction.payerId,
        payeeId:instruction.payeeId,
        currency:instruction.currency,
        amountCents:number(instruction.amountCents),
        purpose:instruction.purpose,
        findingIds:strings(instruction.findingIds),
        state:event?.state ?? (authorized.has(instruction.id) ? "AUTHORIZED" : "PREPARED"),
        provider:event?.provider ?? null,
        providerReference:event?.providerReference ?? null,
        authorized:authorized.has(instruction.id),
        settlementVerification:"UNVERIFIED",
        verifiedRecoveredCents:0,
        createdAt:new Date(instruction.createdAt).toISOString(),
      };
    });
    const output: OutputType = {payments};
    return new Response(superjson.stringify(output),{headers:{"Content-Type":"application/json"}});
  } catch (error) {
    if (error instanceof NotAuthenticatedError) {
      return new Response(superjson.stringify({error:"Not authenticated"}), {status:401});
    }
    const message = error instanceof Error ? error.message : "Payment list failed";
    return new Response(superjson.stringify({error:message}),{status:400});
  }
}
