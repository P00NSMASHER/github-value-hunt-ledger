/** Unpublished QA-only signed financial admission. Production handler copied
 * unchanged elsewhere; this adds a staging extension, not production billing.
 */
import superjson from "superjson";
import { sql } from "kysely";
import { db } from "../../helpers/db";
import { requireRecoveryScopedAccess } from "../../helpers/recoveryTenant";
import { financePayload,verifySyntheticFinancialEnvelope } from "../../helpers/phase5cFinancialEvidence";
import { recoveryHash } from "../../helpers/recoveryHash";
import {z} from "zod";
const schema=z.object({payload:financePayload,signatureB64:z.string().min(80).max(1000)}).strict();
type CaseRow={customer_id:string;invoice_id:string;currency:string};
type KeyRow={role:string;public_key_pem:string;enabled_from:Date;expires_at:Date;revoked_at:Date|null};
type OldRow={record_id:string;body:unknown;signature_b64:string};
type EventRow={id:string;amount_cents:string};
export async function handle(request:Request){
 try{
  const access=await requireRecoveryScopedAccess(request,"payment_event");
  if(access.role!=="owner")throw new Error("QA_OWNER_REQUIRED");
  const {payload,signatureB64}=schema.parse(superjson.parse(await request.text()));
  if(payload.tenantId!==access.tenantId)throw new Error("SIGNED_DOCUMENT_TENANT_MISMATCH");
  const result=await db.transaction().execute(async trx=>{
    const cases=await sql<CaseRow>`SELECT customer_id,invoice_id,currency FROM phase5c_qa.cases
      WHERE tenant_id=${payload.tenantId} AND case_id=${payload.caseId} FOR UPDATE`.execute(trx);
    const c=cases.rows[0];
    if(!c)throw new Error("UNKNOWN_SYNTHETIC_CASE");
    if((c.customer_id??(c as any).customerId)!==payload.customerId||(c.invoice_id??(c as any).invoiceId)!==payload.invoiceId||c.currency!==payload.currency)
      throw new Error("CASE_SOURCE_SCOPE_MISMATCH");
    const keys=await sql<KeyRow>`SELECT role,public_key_pem,enabled_from,expires_at,revoked_at
      FROM phase5c_qa.issuer_keys WHERE tenant_id=${payload.tenantId}
      AND key_id=${payload.issuerKeyId}`.execute(trx);
    const key=keys.rows[0];
    if(!key)throw new Error("UNKNOWN_SYNTHETIC_ISSUER");
    verifySyntheticFinancialEnvelope({payload,signatureB64,issuerRole:key.role,
       publicKeyPem:key.public_key_pem??(key as any).publicKeyPem,validFrom:key.enabled_from??(key as any).enabledFrom,
       expiresAt:key.expires_at??(key as any).expiresAt,revokedAt:key.revoked_at??(key as any).revokedAt??null});
    if(payload.kind==="CARRIER_CREDIT"){
      if(!payload.providerEventId)throw new Error("CARRIER_CREDIT_MISSING_HANDLER_EVENT");
      const ev=await sql<EventRow>`SELECT id,amount_cents FROM public.recovery_payment_events
        WHERE tenant_id=${payload.tenantId} AND id=${payload.providerEventId}
        AND state='SETTLED'`.execute(trx);
      if(ev.rows.length!==1||BigInt(ev.rows[0].amount_cents??(ev.rows[0] as any).amountCents)!==BigInt(payload.amountCents))
        throw new Error("CARRIER_CREDIT_UNBACKED_BY_HANDLER_EVENT");
    }else if(payload.providerEventId!==null)throw new Error("UNEXPECTED_PROVIDER_EVENT");
    const old=await sql<OldRow>`SELECT record_id,body,signature_b64 FROM phase5c_qa.documents
      WHERE tenant_id=${payload.tenantId} AND record_id=${payload.recordId}`.execute(trx);
    if(old.rows.length){
       if(recoveryHash(old.rows[0].body as any)!==recoveryHash(payload as any)||(old.rows[0].signature_b64??(old.rows[0] as any).signatureB64)!==signatureB64)
         throw new Error("CONFLICTING_RECORD_REPLAY");
       return {recordId:old.rows[0].record_id??(old.rows[0] as any).recordId,replay:true};
    }
    // A historic occurrence timestamp is not proof of when a document was
    // signed or submitted. New admissions require currently active keys.
    // Previously admitted exact replays above remain read-only/idempotent.
    const revokedAt=key.revoked_at??(key as any).revokedAt??null;
    const expiresAt=key.expires_at??(key as any).expiresAt;
    if((revokedAt!==null && Date.now()>=new Date(revokedAt).getTime()) ||
        Date.now()>=new Date(expiresAt).getTime())
      throw new Error("SYNTHETIC_SIGNER_NO_LONGER_TRUSTED_FOR_NEW_ADMISSION");
    const put=await sql<{record_id:string}>`INSERT INTO phase5c_qa.documents
      (tenant_id,case_id,record_id,kind,economic_key,reference_id,amount_cents,fee_bps,
       currency,occurred_at,source_sha256,issuer_key_id,body,signature_b64)
      VALUES(${payload.tenantId},${payload.caseId},${payload.recordId},${payload.kind},
        ${payload.economicKey},${payload.referenceId},${payload.amountCents},${payload.feeBps},
        ${payload.currency},${new Date(payload.occurredAt)},${payload.sourceHash},
        ${payload.issuerKeyId},${payload}::jsonb,${signatureB64})
      RETURNING record_id`.execute(trx);
    return {recordId:put.rows[0].record_id??(put.rows[0] as any).recordId,replay:false};
  });
  return new Response(superjson.stringify({...result,classification:"FICTIONAL_SIGNED_QA_ONLY",
     actualCustomerRecoveryProven:false}),{status:200,headers:{"content-type":"application/json"}});
 }catch(error){
  return new Response(superjson.stringify({error:error instanceof Error?error.message:"QA_EVIDENCE_REJECTED"}),
     {status:400,headers:{"content-type":"application/json"}});
 }
}
