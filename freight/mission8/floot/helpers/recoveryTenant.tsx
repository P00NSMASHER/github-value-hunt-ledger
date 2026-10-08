import { nanoid } from "nanoid";
import { createHash } from "node:crypto";
import { db } from "./db";
import { getServerUserSession } from "./getServerUserSession";
import { requireSameOriginMutation } from "./requestSecurity";

export type TenantAccess = {
  tenantId: string;
  tenantName: string;
  role: "owner" | "reviewer" | "viewer";
  userId: number;
};

export type IngestAccess = {
  tenantId: string;
  tenantName: string;
  principal: "human" | "api_key";
  userId: number | null;
  role: "owner" | "reviewer" | "api_key";
};

export type ApiScope = "ingest" | "payment_event";

export async function requireRecoveryTenant(request: Request): Promise<TenantAccess> {
  requireSameOriginMutation(request);
  const { user } = await getServerUserSession(request);
  const membership = await db
    .selectFrom("recoveryTenantMemberships")
    .innerJoin("recoveryTenants", "recoveryTenantMemberships.tenantId", "recoveryTenants.id")
    .select([
      "recoveryTenantMemberships.tenantId as tenantId",
      "recoveryTenantMemberships.role as role",
      "recoveryTenants.name as tenantName",
    ])
    .where("recoveryTenantMemberships.userId", "=", String(user.id))
    .orderBy("recoveryTenantMemberships.createdAt", "asc")
    .limit(1)
    .executeTakeFirst();

  if (membership) {
    return {
      tenantId: membership.tenantId,
      tenantName: membership.tenantName,
      role: membership.role as TenantAccess["role"],
      userId: user.id,
    };
  }

  const tenantId = "rt_" + nanoid(18);
  const safeName = user.displayName?.trim() || user.email;
  const slug = ("workspace-" + user.id + "-" + nanoid(6)).toLowerCase();
  await db.transaction().execute(async trx => {
    await trx.insertInto("recoveryTenants").values({
      id: tenantId,
      name: safeName + " Freight Recovery",
      slug,
    }).execute();
    await trx.insertInto("recoveryTenantMemberships").values({
      tenantId,
      userId: user.id,
      role: "owner",
    }).execute();
  });
  return { tenantId, tenantName: safeName + " Freight Recovery", role: "owner", userId: user.id };
}

export function requireReviewPermission(access: TenantAccess) {
  if (!["owner", "reviewer"].includes(access.role)) {
    throw new Error("Reviewer permission required");
  }
}

export async function requireRecoveryScopedAccess(request: Request, requiredScope: ApiScope): Promise<IngestAccess> {
  const authorization = request.headers.get("authorization") || "";
  if (authorization.startsWith("Bearer ")) {
    const token = authorization.slice("Bearer ".length).trim();
    if (!token.startsWith("frk_") || token.length < 30) throw new Error("Invalid RecoveryOS API key");
    const keyHash = createHash("sha256").update(token).digest("hex");
    const key = await db
      .selectFrom("recoveryApiKeys")
      .innerJoin("recoveryTenants", "recoveryApiKeys.tenantId", "recoveryTenants.id")
      .select([
        "recoveryApiKeys.tenantId as tenantId",
        "recoveryApiKeys.scope as scope",
        "recoveryApiKeys.revokedAt as revokedAt",
        "recoveryTenants.name as tenantName",
      ])
      .where("recoveryApiKeys.keyHash", "=", keyHash)
      .limit(1)
      .executeTakeFirst();
    if (!key || key.revokedAt || key.scope !== requiredScope) throw new Error("RecoveryOS API key not authorized for " + requiredScope);
    return { tenantId: key.tenantId, tenantName: key.tenantName, principal: "api_key", userId: null, role: "api_key" };
  }
  const human = await requireRecoveryTenant(request);
  requireReviewPermission(human);
  return { tenantId: human.tenantId, tenantName: human.tenantName, principal: "human", userId: human.userId, role: human.role as "owner" | "reviewer" };
}

export async function requireRecoveryIngestAccess(request: Request): Promise<IngestAccess> {
  return requireRecoveryScopedAccess(request, "ingest");
}
