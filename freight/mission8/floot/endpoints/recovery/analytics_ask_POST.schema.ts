import { z } from "zod";
import superjson from "superjson";

export const schema = z.object({
  question: z.string().min(3).max(1000),
});
export type InputType = z.infer<typeof schema>;
export type AnalyticsRow = { label: string; value: number; valueType: "count" | "cents"; currency?: string };
export type OutputType = {
  intent: string;
  confidence: number;
  answer: string;
  rows: AnalyticsRow[];
  creditsConsumed: number;
};

export async function postAnalyticsAsk(body: InputType, init?: RequestInit): Promise<OutputType> {
  const validated = schema.parse(body);
  const response = await fetch("/_api/recovery/analytics_ask", {
    method:"POST",
    body:superjson.stringify(validated),
    ...init,
    headers:{"Content-Type":"application/json",...(init?.headers ?? {})},
  });
  if (!response.ok) {
    const error = superjson.parse<{error:string;code?:string}>(await response.text());
    const e = new Error(error.error);
    (e as any).code = error.code;
    throw e;
  }
  return superjson.parse<OutputType>(await response.text());
}
