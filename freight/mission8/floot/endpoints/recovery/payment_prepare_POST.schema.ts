import { z } from "zod";
import superjson from "superjson";

export const schema = z.object({
  payerId: z.string().min(1).max(256),
  payeeId: z.string().min(1).max(256),
  currency: z.string().regex(/^[A-Z]{3}$/),
  amountCents: z.number().int().positive().safe(),
  purpose: z.string().min(3).max(1000),
  findingIds: z.array(z.string().min(1).max(160)).min(1).max(500),
  idempotencyKey: z.string().min(8).max(200),
});
export type InputType = z.infer<typeof schema>;
export type OutputType = {
  instructionId: string;
  instructionHash: string;
  status: "PREPARED";
};

export async function postPaymentPrepare(body: InputType, init?: RequestInit): Promise<OutputType> {
  const validated = schema.parse(body);
  const response = await fetch("/_api/recovery/payment_prepare", {
    method: "POST",
    body: superjson.stringify(validated),
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const error = superjson.parse<{error:string}>(await response.text());
    throw new Error(error.error);
  }
  return superjson.parse<OutputType>(await response.text());
}

