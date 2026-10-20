import superjson from "superjson";

export type ReviewItem = {
  id: string;
  carrier: string;
  invoice: string;
  category: string;
  billedCents: number;
  expectedCents: number;
  varianceCents: number;
  confidencePpm: number;
  attributionState: string;
  blockerCodes: string[];
  evidence: string[];
  findingHash: string;
  currency: string;
};

export type OutputType = {
  tenant: { id: string; name: string; role: string };
  totals: {
    recordsReviewed: number;
    findings: number;
    challengerOnly: number;
    candidateDifferenceCents: number;
    candidateDifferenceCurrency: "USD";
    candidateByCurrency: Array<{currency:string;candidateDifferenceCents:number;netNewCandidateCents:number}>;
    confirmedCount: number;
  };
  reviewQueue: ReviewItem[];
};

export async function getRecoveryDashboard(init?: RequestInit): Promise<OutputType> {
  const response = await fetch("/_api/recovery/dashboard", { method: "GET", ...init });
  if (!response.ok) {
    const error = superjson.parse<{error:string}>(await response.text());
    throw new Error(error.error);
  }
  return superjson.parse<OutputType>(await response.text());
}
