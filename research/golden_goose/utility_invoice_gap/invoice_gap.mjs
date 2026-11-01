// Offline synthetic demonstration. A missing invoice is a REVIEW, never a refund or proven liability.
export function auditInvoiceContinuity(account,invoices,asOf,graceDays=45){
  const issue=(status,month=null)=>({account_id: typeof account?.id==="string"?account.id:"UNKNOWN",month,status,recoverable_cents:null,potential_liability_cents:null,realized_revenue_cents:0});
  const strictDate=(value)=>{
    if(typeof value!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
    const d=new Date(value+"T00:00:00Z");
    return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value?d:null;
  };
  const now=strictDate(asOf);
  if(!now||!Array.isArray(invoices)||!Number.isInteger(graceDays)||graceDays<0||graceDays>365)return [issue("INVALID_INPUT_REVIEW")];
  if(!account||typeof account.id!=="string"||!account.id.trim()||account.cadence!=="monthly")return [issue("UNSUPPORTED_ACCOUNT_REVIEW")];
  const first=strictDate(account.service_start);
  const last=account.service_end===null||account.service_end===undefined?now:strictDate(account.service_end);
  if(!first||!last||first>last||first.getUTCDate()!==1||(account.service_end!=null&&last.getUTCDate()!==new Date(Date.UTC(last.getUTCFullYear(),last.getUTCMonth()+1,0)).getUTCDate()))return [issue("UNRESOLVED_SERVICE_BOUNDARY_REVIEW")];
  const relevant=invoices.filter(x=>x&&x.account_id===account.id);
  if(relevant.some(x=>typeof x.bill_month!=="string"||!/^\d{4}-(0[1-9]|1[0-2])$/.test(x.bill_month)||typeof x.invoice_id!=="string"||!x.invoice_id.trim()))return [issue("INVALID_INVOICE_SOURCE_REVIEW")];
  const rows=[];
  let y=first.getUTCFullYear(),m=first.getUTCMonth()+1;
  const horizon=last<now?last:now;
  for(let n=0;n<240;n++){
    const monthFirst=new Date(Date.UTC(y,m-1,1));
    if(monthFirst>horizon)break;
    const monthEnd=new Date(Date.UTC(y,m,0));
    const eligibleOn=new Date(monthEnd.getTime()+graceDays*86400000);
    const month=String(y).padStart(4,"0")+"-"+String(m).padStart(2,"0");
    if(monthEnd<=horizon&&eligibleOn<=now){
      const candidates=relevant.filter(x=>x.bill_month===month);
      let status="INVOICE_PRESENT";
      if(!candidates.length)status="MISSING_INVOICE_REVIEW";
      else if(candidates.some(x=>!["posted","void","draft"].includes(x.status)||!Number.isSafeInteger(x.amount_cents)||x.amount_cents<0))status="INVALID_INVOICE_SOURCE_REVIEW";
      else if(new Set(candidates.map(x=>x.invoice_id)).size!==candidates.length)status="DUPLICATE_SOURCE_RECORD_REVIEW";
      else {
        const posted=candidates.filter(x=>x.status==="posted");
        if(posted.length>1)status="MULTIPLE_POSTED_INVOICES_REVIEW";
        else if(!posted.length)status="NO_POSTED_INVOICE_REVIEW";
        else if(posted[0].amount_cents===0)status="ZERO_AMOUNT_REVIEW";
      }
      rows.push(issue(status,month));
    }
    m++;if(m===13){m=1;y++;}
  }
  return rows;
}
