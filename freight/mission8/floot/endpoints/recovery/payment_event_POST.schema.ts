import { z } from "zod";
import superjson from "superjson";

export const schema = z.object({
  instructionId: z.string().min(1).max(160),
  state: z.enum(["SUBMITTED","ACCEPTED","SETTLED","FAILED","REVERSED"]),
  provider: z.string().min(1).max(120),
  providerReference: z.string().min(1).max(256).nullable().optional(),
  amountCents: z.number().int().positive().safe(),
  sourceHash: z.string().regex(/^[0-9a-f]{64}$/),
  occurredAt: z.string().datetime({offset:true}),
});
export type InputType = z.infer<typeof schema>;
export type OutputType = { eventId: string; eventHash: string; state: string };

export async function postPaymentEvent(body: InputType, init?: RequestInit): Promise<OutputType> {
  const validated = schema.parse(body);
  const response = await fetch("/_api/recovery/payment_event", {
    method:"POST",
    body:superjson.stringify(validated),
    ...init,
    headers:{"Content-Type":"application/json",...(init?.headers ?? {})},
  });
  if (!response.ok) {
    const error = superjson.parse<{error:string}>(await response.text());
    throw new Error(error.error);
  }
  return superjson.parse<OutputType>(await response.text());
}

