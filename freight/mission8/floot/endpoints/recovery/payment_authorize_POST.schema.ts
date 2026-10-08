import { z } from "zod";
import superjson from "superjson";

export const schema = z.object({
  instructionId: z.string().min(1).max(160),
  reason: z.string().min(3).max(2000),
});
export type InputType = z.infer<typeof schema>;
export type OutputType = {
  authorizationId: string;
  authorizationHash: string;
  status: "AUTHORIZED";
};

export async function postPaymentAuthorize(body: InputType, init?: RequestInit): Promise<OutputType> {
  const validated = schema.parse(body);
  const response = await fetch("/_api/recovery/payment_authorize", {
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

