/** Phase 5C QA-only cryptographic admission. Uses externally generated fictional
 * Ed25519 public keys; the source writer has no signer private key.
 * A valid synthetic signature is NOT evidence of real customer recovery.
 */
import { createPublicKey, verify as ed25519Verify } from "node:crypto";
import { z } from "zod";

export const financePayload = z.object({
  tenantId:z.string().startsWith("SIM-"), caseId:z.string().startsWith("SIM-"),
  recordId:z.string().startsWith("SIM-"),
  customerId:z.string().startsWith("SIM-"),invoiceId:z.string().startsWith("SIM-"),
  kind:z.enum(["CONTRACT","CARRIER_CREDIT","CUSTOMER_POST","CUSTOMER_REVERSAL",
               "FEE_INVOICE","FEE_COLLECTION","FEE_CREDIT","FEE_REFUND"]),
  economicKey:z.string().startsWith("SIM-"),
  referenceId:z.string().nullable(),
  amountCents:z.number().int().safe().nonnegative(),
  feeBps:z.number().int().min(1).max(9999).nullable(),
  currency:z.string().regex(/^[A-Z]{3}$/),
  occurredAt:z.string().datetime({offset:true}),
  sourceHash:z.string().regex(/^[a-f0-9]{64}$/),
  issuerKeyId:z.string().startsWith("SIM-"),
  contractVersion:z.string().min(1).max(80),
  // Real copied payment handler event: only links a carrier assertion to
  // an existing event. SETTLED cannot directly create recovered customer cash.
  providerEventId:z.string().nullable(),
}).strict();

export type FinancePayload = z.infer<typeof financePayload>;
export const KIND_ROLE:Record<FinancePayload["kind"],string> = {
  CONTRACT:"BUYER", CARRIER_CREDIT:"CARRIER", CUSTOMER_POST:"BUYER_ACCOUNTING",
  CUSTOMER_REVERSAL:"BUYER_ACCOUNTING",FEE_INVOICE:"RETALLY_BILLING",
  FEE_COLLECTION:"PAYMENT_PROCESSOR",FEE_CREDIT:"RETALLY_BILLING",
  FEE_REFUND:"PAYMENT_PROCESSOR",
};

function normalize(v:unknown):unknown {
  if(Array.isArray(v))return v.map(normalize);
  if(v !== null && typeof v==="object"){
    const obj=v as Record<string,unknown>,out:Record<string,unknown>={};
    for(const k of Object.keys(obj).sort())out[k]=normalize(obj[k]);
    return out;
  }
  return v;
}

export function verifySyntheticFinancialEnvelope(args:{
 payload:FinancePayload; signatureB64:string; publicKeyPem:string;
 issuerRole:string; validFrom:Date|string; expiresAt:Date|string;
 revokedAt:Date|string|null;
}):void {
  const {payload,signatureB64,publicKeyPem,issuerRole}=args;
  if(issuerRole!==KIND_ROLE[payload.kind])throw new Error("SYNTHETIC_ISSUER_ROLE_MISMATCH");
  if(payload.kind==="CONTRACT"){
    if(payload.amountCents!==0 || payload.feeBps===null)throw new Error("INVALID_CONTRACT_TERMS");
  }else if(payload.amountCents<=0 || payload.feeBps!==null)throw new Error("INVALID_EVENT_AMOUNT");
  const occurred=new Date(payload.occurredAt).getTime();
  const validFrom=new Date(args.validFrom).getTime();
  const validTo=new Date(args.expiresAt).getTime();
  const revoked=args.revokedAt===null?Infinity:new Date(args.revokedAt).getTime();
  if(![occurred,validFrom,validTo].every(Number.isFinite) || occurred<validFrom || occurred>=validTo
      || occurred>=revoked)throw new Error("SYNTHETIC_SIGNER_NOT_VALID_AT_EVENT");
  if(typeof signatureB64!=="string"||!/^[A-Za-z0-9+/]+={0,2}$/.test(signatureB64))
    throw new Error("INVALID_SIGNATURE_ENCODING");
  const payloadBytes=Buffer.from(JSON.stringify(normalize(payload)),"utf8");
  let accepted=false;
  try {
    const publicKey=createPublicKey(publicKeyPem);
    accepted=ed25519Verify(null,payloadBytes,publicKey,Buffer.from(signatureB64,"base64"));
  }catch{throw new Error("INVALID_SIGNING_KEY_OR_SIGNATURE")}
  if(!accepted)throw new Error("UNTRUSTED_SYNTHETIC_SIGNATURE");
  // Verify signature over every amount, identity, reference, contract version
  // and provenance field; the database separately enforces economic conservation.
}

