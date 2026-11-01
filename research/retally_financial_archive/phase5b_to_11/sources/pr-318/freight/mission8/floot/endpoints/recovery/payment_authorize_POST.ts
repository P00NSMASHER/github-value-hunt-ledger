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
    if (access.role !== "owner") return new Response(superjson.stringify({error:"Owner permission required for payment authorization"}), {status:403});
    const input = schema.parse(superjson.parse(await request.text()));
    const instruction = await db.selectFrom("recoveryPaymentInstructions")
      .select(["id","amountCents","instructionHash"])
      .where("tenantId","=",access.tenantId)
      .where("id","=",input.instructionId)
      .executeTakeFirst();
    if (!instruction) throw new Error("Payment instruction not found");
    const existing = await db.selectFrom("recoveryPaymentAuthorizations")
      .select(["id","authorizationHash"])
      .where("tenantId","=",access.tenantId)
      .where("instructionId","=",instruction.id)
      .executeTakeFirst();
    if (existing) {
      const output: OutputType = {authorizationId:existing.id,authorizationHash:existing.authorizationHash,status:"AUTHORIZED"};
      return new Response(superjson.stringify(output), {headers:{"Content-Type":"application/json"}});
    }
    const id = "pauth_" + nanoid(18);
    const amount = Number(instruction.amountCents);
    if (!Number.isSafeInteger(amount) || amount <= 0) throw new Error("Unsafe instruction amount");
    const authorizationHash = recoveryHash({
      schema:1,
      tenant_id:access.tenantId,
      instruction_hash:instruction.instructionHash,
      authorized_cents:amount,
      authorized_by:access.userId,
      reason:input.reason.trim(),
    });
    await db.insertInto("recoveryPaymentAuthorizations").values({
      id,
      tenantId:access.tenantId,
      instructionId:instruction.id,
      authorizedCents:amount,
      authorizedBy:access.userId,
      reason:input.reason.trim(),
      authorizationHash,
    }).execute();
    const output: OutputType = {authorizationId:id,authorizationHash,status:"AUTHORIZED"};
    return new Response(superjson.stringify(output), {headers:{"Content-Type":"application/json"}});
  } catch (error) {
    if (error instanceof NotAuthenticatedError) {
      return new Response(superjson.stringify({error:"Not authenticated"}), {status:401});
    }
    const message = error instanceof Error ? error.message : "Payment authorization failed";
    return new Response(superjson.stringify({error:message}), {status:400});
  }
}

