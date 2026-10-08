import { nanoid } from "nanoid";
import superjson from "superjson";
import { db } from "../../helpers/db";
import { recoveryHash } from "../../helpers/recoveryHash";
import { requireRecoveryScopedAccess } from "../../helpers/recoveryTenant";
import { NotAuthenticatedError } from "../../helpers/getSetServerSession";
import { resolveProviderEvent } from "../../helpers/recoveryPaymentReplay";
import { schema, OutputType } from "./payment_event_POST.schema";

export async function handle(request: Request) {
  try {
    const access = await requireRecoveryScopedAccess(request, "payment_event");
    if (access.principal === "human" && access.role !== "owner") {
      return new Response(superjson.stringify({error:"Owner permission required for manual payment lifecycle events"}), {status:403});
    }
    const input = schema.parse(superjson.parse(await request.text()));

    // Serialize every payment-event transition for this tenant/instruction on the
    // actual PostgreSQL instruction row. READ COMMITTED ensures a later transaction
    // sees events committed by the prior holder of the FOR UPDATE row lock.
    // A helper-only replay check on an unlocked snapshot is insufficient.
    const output: OutputType = await db.transaction().execute(async (trx) => {
      const instruction = await trx.selectFrom("recoveryPaymentInstructions")
        .select(["id","amountCents","instructionHash"])
        .where("tenantId","=",access.tenantId)
        .where("id","=",input.instructionId)
        .forUpdate()
        .executeTakeFirst();
      if (!instruction) throw new Error("Payment instruction not found");
      if (input.amountCents !== Number(instruction.amountCents)) {
        throw new Error("Provider event amount must match the authorized instruction amount");
      }
      const authorization = await trx.selectFrom("recoveryPaymentAuthorizations")
        .select("id")
        .where("tenantId","=",access.tenantId)
        .where("instructionId","=",instruction.id)
        .executeTakeFirst();
      const events = await trx.selectFrom("recoveryPaymentEvents")
        .select(["id","eventHash","state","provider","providerReference","amountCents","sourceHash","occurredAt"])
        .where("tenantId","=",access.tenantId)
        .where("instructionId","=",instruction.id)
        .orderBy("occurredAt","asc")
        .orderBy("createdAt","asc")
        .execute();
      // Replays return the ORIGINAL event, including after later states.
      // New transitions require current authorization, including reversals.
      const decision = resolveProviderEvent(input, events, Boolean(authorization));
      if (decision.kind === "REPLAY") {
        return {eventId:decision.eventId,eventHash:decision.eventHash,state:input.state};
      }
      const eventHash = recoveryHash({
        schema:1,
        tenant_id:access.tenantId,
        instruction_hash:instruction.instructionHash,
        prior_state:decision.priorState,
        state:input.state,
        provider:input.provider,
        provider_reference:input.providerReference ?? null,
        amount_cents:input.amountCents,
        source_hash:input.sourceHash,
        occurred_at:decision.occurredAt.toISOString(),
      });
      const existing = await trx.selectFrom("recoveryPaymentEvents")
        .select("id")
        .where("tenantId","=",access.tenantId)
        .where("eventHash","=",eventHash)
        .executeTakeFirst();
      if (existing) {
        return {eventId:existing.id,eventHash,state:input.state};
      }
      const eventId = "pe_" + nanoid(18);
      await trx.insertInto("recoveryPaymentEvents").values({
        id:eventId,
        tenantId:access.tenantId,
        instructionId:instruction.id,
        state:input.state,
        provider:input.provider,
        providerReference:input.providerReference ?? null,
        amountCents:input.amountCents,
        sourceHash:input.sourceHash,
        occurredAt:decision.occurredAt,
        eventHash,
      }).execute();
      return {eventId,eventHash,state:input.state};
    });
    return new Response(superjson.stringify(output), {headers:{"Content-Type":"application/json"}});
  } catch (error) {
    if (error instanceof NotAuthenticatedError) {
      return new Response(superjson.stringify({error:"Not authenticated"}), {status:401});
    }
    const message = error instanceof Error ? error.message : "Payment event failed";
    return new Response(superjson.stringify({error:message}), {status:400});
  }
}

