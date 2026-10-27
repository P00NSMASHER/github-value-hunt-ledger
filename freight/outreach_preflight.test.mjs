import { mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { OPT_OUT, outreachApprovalDigest } from "./outreach_guard.mjs";
const exec=promisify(execFile), dir=mkdtempSync(join(tmpdir(),"synthetic-outreach-"));
const cli=new URL("./outreach_preflight.mjs",import.meta.url).pathname;
const msg=join(dir,"message.json"), ledger=join(dir,"ledger.json"), sender=join(dir,"sender.json");
const message={to:"test@example.com",account_id:"synthetic",subject:"Review",channel:"EDITORIAL",touch:1,
 text:"Synthetic Sender\n123 Example Street\nExampletown, PA 19000\n"+OPT_OUT};
const config={identity:"Synthetic Sender",postal_approved:true,postal_lines:["123 Example Street","Exampletown, PA 19000"]};
function reset() {
 const approvedAt=new Date();
 const ownerApproval={confirmed_by_owner:true,approved_by:"OWNER",
  approval_id:"synthetic-private-approval-20261019",
  evidence_ref:"private:synthetic-operator-review",
  recipient_key:message.to,account_id:message.account_id,
  channel:message.channel,touch:message.touch,
  approved_at:approvedAt.toISOString(),
  expires_at:new Date(approvedAt.getTime()+60*60*1000).toISOString(),
  message_sha256:outreachApprovalDigest(message)};
 writeFileSync(msg,JSON.stringify(message));
 writeFileSync(sender,JSON.stringify({...config,owner_approval:ownerApproval}));
 writeFileSync(ledger,JSON.stringify({schema_version:1,audit_hold:false,mailbox_checked_at:new Date().toISOString(),
 contacts:[{recipient_key:message.to,account_id:"synthetic",route_verified:true,channel_approved:true,suppressed:false,hold:false}],
 events:[]}));
}
function assert(v,m) {if(!v)throw new Error(m);}
try {
 reset();
 const attempts=await Promise.allSettled([
  exec(process.execPath,[cli,msg,ledger,sender,"worker-one"]),
  exec(process.execPath,[cli,msg,ledger,sender,"worker-two"])
 ]);
 assert(attempts.filter(r=>r.status==="fulfilled").length===1,"exactly one concurrent reservation");
 assert(JSON.parse(readFileSync(ledger,"utf8")).events.length===1,"one durable reservation");
 assert(attempts.filter(r=>r.status==="rejected").every(r=>/LEDGER_LOCKED|UNRESOLVED_PRIOR_SEND/.test(r.reason.stderr)),"second worker blocked");
 const output=attempts.find(r=>r.status==="fulfilled").value.stdout;
 assert(!output.includes("test@example.com") && JSON.parse(output).email_sent===false,"no PII or sending");
 // No owner approval means the CLI cannot even reserve a send.
 reset();writeFileSync(sender,JSON.stringify(config));
 const unapproved=await exec(process.execPath,[cli,msg,ledger,sender,"unapproved"]).then(()=>false,e=>/EXPLICIT_OWNER_APPROVAL_REQUIRED/.test(e.stderr));
 assert(unapproved && JSON.parse(readFileSync(ledger,"utf8")).events.length===0,"missing owner approval fails closed");
 reset();
 const altered=JSON.parse(readFileSync(msg,"utf8"));altered.subject="Retitled after approval";
 writeFileSync(msg,JSON.stringify(altered));
 const tampered=await exec(process.execPath,[cli,msg,ledger,sender,"tampered"]).then(()=>false,e=>/EXPLICIT_OWNER_APPROVAL_REQUIRED/.test(e.stderr));
 assert(tampered && JSON.parse(readFileSync(ledger,"utf8")).events.length===0,"changed subject invalidates approval");
 reset();writeFileSync(ledger+".lock","synthetic stale lock");
 const locked=await exec(process.execPath,[cli,msg,ledger,sender,"locked"]).then(()=>false,e=>/LEDGER_LOCKED/.test(e.stderr));
 assert(locked && readFileSync(ledger+".lock","utf8")==="synthetic stale lock","foreign lock preserved");
 rmSync(ledger+".lock");reset();
 writeFileSync(msg,JSON.stringify({...message,text:"No footer"}));
 const bad=await exec(process.execPath,[cli,msg,ledger,sender,"bad"]).then(()=>false,e=>/OPT_OUT_MISSING/.test(e.stderr));
 assert(bad && JSON.parse(readFileSync(ledger,"utf8")).events.length===0,"invalid message never reserved");
 // Inputs inside the checkout are rejected before the file is interpreted.
 const inside=new URL("./outreach_guard.mjs",import.meta.url).pathname;
 const privateOnly=await exec(process.execPath,[cli,inside,ledger,sender,"inside"]).then(()=>false,e=>/PRIVATE_INPUTS_MUST_BE_OUTSIDE_CHECKOUT/.test(e.stderr));
 assert(privateOnly,"public checkout rejects private inputs");
 console.log("8 private reservation integration checks passed");
} finally { rmSync(dir,{recursive:true,force:true}); }
