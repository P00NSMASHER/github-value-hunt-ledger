/** Deterministic payment event retry policy. No DB, I/O or provider calls. */
export type PaymentLifecycleState = "SUBMITTED" | "ACCEPTED" | "SETTLED" | "FAILED" | "REVERSED";
export type PaymentIncoming = {
  state: PaymentLifecycleState;
  provider: string;
  providerReference?: string | null;
  amountCents: number;
  sourceHash: string;
  occurredAt: string;
};
export type StoredPayment = {
  id: string;
  eventHash: string;
  state: string;
  provider: string;
  providerReference: string | null;
  amountCents: number | string | bigint;
  sourceHash: string;
  occurredAt: Date | string;
};
type Decision =
  | { kind: "REPLAY"; eventId: string; eventHash: string; priorState: string; occurredAt: Date }
  | { kind: "APPEND"; priorState: string; occurredAt: Date };

const ALLOWED: Record<string, ReadonlyArray<string>> = {
  PREPARED: [],
  AUTHORIZED: ["SUBMITTED"],
  SUBMITTED: ["ACCEPTED", "FAILED"],
  ACCEPTED: ["SETTLED", "FAILED"],
  SETTLED: ["REVERSED"],
  FAILED: [],
  REVERSED: [],
};

function canonicalTime(value: Date | string): number {
  const dt = value instanceof Date ? value : new Date(value);
  const ms = dt.getTime();
  if (!Number.isFinite(ms)) throw new Error("Invalid provider event timestamp");
  return ms;
}

/** Resolve an exact previously persisted replay before checking current state.
 * Requires a tenant + instruction scoped DB snapshot from the caller.
 * This is NOT provider authentication and does not solve concurrent insert races.
 */
export function resolveProviderEvent(
  incoming: PaymentIncoming,
  history: ReadonlyArray<StoredPayment>,
  hasAuthorization: boolean,
): Decision {
  const at = canonicalTime(incoming.occurredAt);
  const providerReference = incoming.providerReference ?? null;
  for (const old of history) {
    const sameIdentity = old.provider === incoming.provider
      && old.state === incoming.state
      && old.providerReference === providerReference;
    if (!sameIdentity) continue;
    const identical = Number(old.amountCents) === incoming.amountCents
      && old.sourceHash === incoming.sourceHash
      && canonicalTime(old.occurredAt) === at;
    if (!identical) throw new Error("Conflicting provider event replay");
    return { kind:"REPLAY", eventId:old.id, eventHash:old.eventHash,
             priorState:old.state, occurredAt:new Date(at) };
  }
  const last = history[history.length - 1];
  const priorState = last?.state ?? (hasAuthorization ? "AUTHORIZED" : "PREPARED");
  if (!ALLOWED[priorState]?.includes(incoming.state)) {
    throw new Error(`Invalid payment transition ${priorState} -> ${incoming.state}`);
  }
  // Exact historical replays above are read-only; every NEW transition needs
  // current instruction authorization, including ACCEPTED/SETTLED/REVERSED.
  if (!hasAuthorization) {
    throw new Error("Payment state advancement requires instruction authorization");
  }
  if (last && at < canonicalTime(last.occurredAt)) {
    throw new Error("Provider event predates prior payment event");
  }
  return { kind:"APPEND", priorState, occurredAt:new Date(at) };
}

