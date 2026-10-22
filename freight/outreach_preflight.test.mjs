import { mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { OPT_OUT, messageApprovalDigest } from "./outreach_guard.mjs";
const exec=promisify(execFile), dir=mkdtempSync(join(tmpdir(),"synthetic-outreach-"));
const cli=fileURLToPath(new URL("./outreach_preflight.mjs",import.meta.url));
const msg=join(dir,"message.json"), ledger=join(dir,"ledger.json"), sender=join(dir,"sender.json"), approval=join(dir,"approval.json");
const message={to:"test@example.com",account_id:"synthetic",subject:"Review",channel:"EDITORIAL",touch:1,
 text:"Synthetic Sender\n123 Example Street\nExampletown, PA 19000\nAdvertisement - one-time business outreach.\n"+OPT_OUT};
const config={identity:"Synthetic Sender",approval_identity:"Synthetic Owner",postal_approved:true,
 postal_lines:["123 Example Street","Exampletown, PA 19000"],opt_out_text:OPT_OUT,
 commercial_notice_text:"Advertisement - one-time business outreach."};
function reset() {
 writeFileSync(msg,JSON.stringify(message));
 writeFileSync(sender,JSON.stringify(config));
 writeFileSync(approval,JSON.stringify({schema_version:1,approved:true,approved_by:"Synthetic Owner",
  approved_at:new Date().toISOString(),approval_id:"synthetic-owner-approval",message_sha256:messageApprovalDigest(message)}));
 writeFileSync(ledger,JSON.stringify({schema_version:1,audit_hold:false,mailbox_checked_at:new Date().toISOString(),
 contacts:[{recipient_key:message.to,account_id:"synthetic",route_verified:true,channel_approved:true,suppressed:false,hold:false}],
 events:[]}));
}
function assert(v,m) {if(!v)throw new Error(m);}
try {
 reset();
 const attempts=await Promise.allSettled([
  exec(process.execPath,[cli,msg,ledger,sender,approval,"worker-one"]),
  exec(process.execPath,[cli,msg,ledger,sender,approval,"worker-two"])
 ]);
 assert(attempts.filter(r=>r.status==="fulfilled").length===1,"exactly one concurrent reservation: "+
  JSON.stringify(attempts.map(r=>r.status==="fulfilled"?r.value.stdout:r.reason.stderr)));
 assert(JSON.parse(readFileSync(ledger,"utf8")).events.length===1,"one durable reservation");
 assert(attempts.filter(r=>r.status==="rejected").every(r=>/LEDGER_LOCKED|UNRESOLVED_PRIOR_SEND/.test(r.reason.stderr)),"second worker blocked");
 const output=attempts.find(r=>r.status==="fulfilled").value.stdout;
 assert(!output.includes("test@example.com") && JSON.parse(output).email_sent===false,"no PII or sending");
 reset();writeFileSync(ledger+".lock","synthetic stale lock");
 const locked=await exec(process.execPath,[cli,msg,ledger,sender,approval,"locked"]).then(()=>false,e=>/LEDGER_LOCKED/.test(e.stderr));
 assert(locked && readFileSync(ledger+".lock","utf8")==="synthetic stale lock","foreign lock preserved");
 rmSync(ledger+".lock");reset();
 writeFileSync(msg,JSON.stringify({...message,text:"No footer"}));
 const bad=await exec(process.execPath,[cli,msg,ledger,sender,approval,"bad"]).then(()=>false,e=>/OPT_OUT_MISSING/.test(e.stderr));
 assert(bad && JSON.parse(readFileSync(ledger,"utf8")).events.length===0,"invalid message never reserved");
 // Inputs inside the checkout are rejected before the file is interpreted.
 const inside=fileURLToPath(new URL("./outreach_guard.mjs",import.meta.url));
 const privateOnly=await exec(process.execPath,[cli,inside,ledger,sender,approval,"inside"]).then(()=>false,e=>/PRIVATE_INPUTS_MUST_BE_OUTSIDE_CHECKOUT/.test(e.stderr));
 assert(privateOnly,"public checkout rejects private inputs");
 console.log("6 private reservation integration checks passed");
} finally { rmSync(dir,{recursive:true,force:true}); }
