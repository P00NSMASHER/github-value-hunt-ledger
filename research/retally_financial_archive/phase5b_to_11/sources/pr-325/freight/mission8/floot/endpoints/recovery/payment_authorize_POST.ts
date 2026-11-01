import { nanoid } from "nanoid";
import superjson from "superjson";
import { db } from "../../helpers/db";
import { recoveryHash } from "../../helpers/recoveryHash";
import { requireRecoveryTenant } from "../../helpers/recoveryTenant";
import { NotAuthenticatedError } from "../../helpers/getSetServerSession";
import { schema, OutputType } from "./payment_authorize_POST.schema";

export async function handle(request: Request) {
  try {
    const access = await requireRecoveryTenant(request);
    if (access.role !== "owner") {
      return new Response(superjson.stringify({error:"Owner permission required for payment authorization"}), {status:403});
    }
    const input = schema.parse(superjson.parse(await request.text()));

    // The payment instruction is the serialization key for authorization AND
    // event transitions. The event endpoint also locks this same instruction.
    // All authorization reads and writes must use this transaction connection.
    const output: OutputType = await db.transaction().execute(async trx => {
      const instruction = await trx.selectFrom("recoveryPaymentInstructions")
        .select(["id","amountCents","instructionHash"])
        .where("tenantId","=",access.tenantId)
        .where("id","=",input.instructionId)
        .forUpdate()
        .executeTakeFirst();
      if (!instruction) throw new Error("Payment instruction not found");

      const existing = await trx.selectFrom("recoveryPaymentAuthorizations")
        .select(["id","authorizationHash"])
        .where("tenantId","=",access.tenantId)
        .where("instructionId","=",instruction.id)
        .executeTakeFirst();
      if (existing) {
        return {authorizationId:existing.id,authorizationHash:existing.authorizationHash,status:"AUTHORIZED" as const};
      }

      const amount = Number(instruction.amountCents);
      if (!Number.isSafeInteger(amount) || amount <= 0) {
        throw new Error("Unsafe instruction amount");
      }
      const reason = input.reason.trim();
      const authorizationHash = recoveryHash({
        schema:1,
        tenant_id:access.tenantId,
        instruction_hash:instruction.instructionHash,
        authorized_cents:amount,
        authorized_by:access.userId,
        reason,
      });
      const authorizationId = "pauth_" + nanoid(18);
      await trx.insertInto("recoveryPaymentAuthorizations").values({
        id:authorizationId,
        tenantId:access.tenantId,
        instructionId:instruction.id,
        authorizedCents:amount,
        authorizedBy:access.userId,
        reason,
        authorizationHash,
      }).execute();
      return {authorizationId,authorizationHash,status:"AUTHORIZED" as const};
    });
    return new Response(superjson.stringify(output), {headers:{"Content-Type":"application/json"}});
  } catch (error) {
    if (error instanceof NotAuthenticatedError) {
      return new Response(superjson.stringify({error:"Not authenticated"}), {status:401});
    }
    const message = error instanceof Error ? error.message : "Payment authorization failed";
    return new Response(superjson.stringify({error:message}), {status:400});
  }
}
