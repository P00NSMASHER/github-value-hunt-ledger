import superjson from "superjson";

export type PaymentRow = {
  id: string;
  payerId: string;
  payeeId: string;
  currency: string;
  amountCents: number;
  purpose: string;
  findingIds: string[];
  state: string;
  provider: string | null;
  providerReference: string | null;
  authorized: boolean;
  settlementVerification: "UNVERIFIED";
  verifiedRecoveredCents: number;
  createdAt: string;
};

export type OutputType = { payments: PaymentRow[] };

export async function getRecoveryPayments(init?: RequestInit): Promise<OutputType> {
  const response = await fetch("/_api/recovery/payments", { method:"GET", ...init });
  if (!response.ok) {
    const error = superjson.parse<{error:string}>(await response.text());
    throw new Error(error.error);
  }
  return superjson.parse<OutputType>(await response.text());
}
