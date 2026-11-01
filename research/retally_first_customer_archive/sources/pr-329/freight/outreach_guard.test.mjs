import { OPT_OUT, messageApprovalDigest, recipientKey, reserveOutreach } from "./outreach_guard.mjs";
function assert(v, msg) { if (!v) throw new Error(msg); }
const now="2026-10-07T20:30:00Z";
const sender={identity:"Synthetic Freight Audit",approval_identity:"Synthetic Owner",postal_approved:true,
 postal_lines:["123 Example Road","Exampletown, PA 19000"],opt_out_text:OPT_OUT,
 commercial_notice_text:"Advertisement - one-time business outreach."};
const q={icp_version:"ICP_V1",approved:true,score:80,us_distributor_or_multisite_shipper:true,target_scale_band:true,
 meaningful_ltl_or_parcel:true,history_months:6,finance_owner_verified:true,disqualified:false,mature_controls:false,
 evidence:["https://example.com/research"]};
function fixture() {
 const m={to:"buyer@example.com",account_id:"synthetic-account",subject:"Freight review",channel:"BUYER",touch:1,
 offer:"FIRST_LOOK",personalization:"Your distribution network.",text:"Your distribution network.\nSynthetic Freight Audit\n123 Example Road\nExampletown, PA 19000\n"+sender.commercial_notice_text+"\n"+OPT_OUT};
 return {m,s:{schema_version:1,audit_hold:false,mailbox_checked_at:now,contacts:[{recipient_key:m.to,account_id:m.account_id,
 route_verified:true,suppressed:false,hold:false,status:"NO_REPLY",qualification:q}],events:[]},a:structuredClone(sender)};
}
let count=0;
function approvalFor(message) {
 return {schema_version:1,approved:true,approved_by:"Synthetic Owner",approved_at:now,
  approval_id:"approval-"+count,message_sha256:messageApprovalDigest(message)};
}
function check(name, edit, reason, editApproval=()=>{}) {
 const f=fixture(); edit(f); const p=approvalFor(f.m); editApproval(p,f);
 const r=reserveOutreach(f.m,f.s,f.a,p,now,"reservation-"+count++);
 assert(reason?(!r.ok && r.errors.includes(reason)):r.ok,name+" "+JSON.stringify(r.errors));
}
check("valid plain",()=>{},null);
check("curly quotes",f=>f.m.text=f.m.text.replace(/"/g,"“").replace(/'/g,"’"),null);
check("valid HTML",f=>f.m.html=f.m.text.replace(/\n/g,"<br>").replace(/"/g,"&quot;").replace(/'/g,"&#39;"),null);
check("literal address placeholder",f=>f.m.text+="\n[VALID BUSINESS POSTAL ADDRESS REQUIRED BEFORE SEND]","UNRESOLVED_PLACEHOLDER");
check("subject placeholder",f=>f.m.subject="{{company}}","UNRESOLVED_PLACEHOLDER");
check("legacy name placeholder",f=>f.m.text+=" [Name]","UNRESOLVED_PLACEHOLDER");
check("HTML only placeholder",f=>f.m.html=f.m.text+" {{company}}","UNRESOLVED_PLACEHOLDER");
check("no sender",f=>f.a={},"APPROVED_SENDER_POSTAL_REQUIRED");
check("unapproved postal",f=>f.a.postal_approved=false,"APPROVED_SENDER_POSTAL_REQUIRED");
check("missing configured opt out",f=>delete f.a.opt_out_text,"SENDER_OPT_OUT_REQUIRED");
check("missing commercial notice config",f=>delete f.a.commercial_notice_text,"COMMERCIAL_NOTICE_REQUIRED");
check("missing commercial notice body",f=>f.m.text=f.m.text.replace(f.a.commercial_notice_text,""),"COMMERCIAL_NOTICE_MISSING_0");
check("owner approval required",()=>{},"OWNER_APPROVAL_REQUIRED",p=>p.approved=false);
check("wrong approver",()=>{},"OWNER_APPROVAL_REQUIRED",p=>p.approved_by="Different Owner");
check("message changed after approval",()=>{},"OWNER_APPROVAL_MESSAGE_MISMATCH",p=>p.message_sha256="0".repeat(64));
check("partial address",f=>f.a.postal_lines=["123 Example Road"],"APPROVED_SENDER_POSTAL_REQUIRED");
check("missing body address",f=>f.m.text=f.m.text.replace("123 Example Road",""),"SENDER_POSTAL_MISSING_0");
check("missing opt out",f=>f.m.text=f.m.text.replace(OPT_OUT,""),"OPT_OUT_MISSING_0");
check("HTML opt out missing",f=>f.m.html=f.m.text.replace(OPT_OUT,""),"OPT_OUT_MISSING_1");
check("HTML script not footer",f=>f.m.html=f.m.text.replace(OPT_OUT,"<script>"+OPT_OUT+"</script>"),"OPT_OUT_MISSING_1");
check("cc blocked",f=>f.m.cc="other@example.com","CC_BCC_NOT_ALLOWED");
check("multi recipient blocked",f=>f.m.to+=",other@example.com","SINGLE_RECIPIENT_REQUIRED");
check("stale mailbox",f=>f.s.mailbox_checked_at="2026-10-07T20:19:59Z","MAILBOX_RECHECK_REQUIRED");
check("audit hold default",f=>delete f.s.audit_hold,"AUDIT_HOLD");
check("unknown contact",f=>f.s.contacts=[],"RESEARCHED_CONTACT_REQUIRED");
check("unverified route",f=>f.s.contacts[0].route_verified=false,"OFFICIAL_ROUTE_REQUIRED");
check("opt out",f=>f.s.contacts[0].status="OPT_OUT","SUPPRESSED");
check("negative",f=>f.s.contacts[0].status="NEGATIVE","SUPPRESSED");
check("hard bounce",f=>f.s.contacts[0].status="HARD_BOUNCE","SUPPRESSED");
check("hold",f=>f.s.contacts[0].hold=true,"CONTACT_HOLD");
check("ICP unapproved",f=>f.s.contacts[0].qualification={...q,approved:false},"ICP_QUALIFICATION_REQUIRED");
check("wrong sector",f=>f.s.contacts[0].qualification={...q,us_distributor_or_multisite_shipper:false},"ICP_QUALIFICATION_REQUIRED");
check("below tier B",f=>f.s.contacts[0].qualification={...q,score:64},"ICP_QUALIFICATION_REQUIRED");
check("history insufficient",f=>f.s.contacts[0].qualification={...q,history_months:5},"ICP_QUALIFICATION_REQUIRED");
check("mature control offer",f=>f.s.contacts[0].qualification={...q,mature_controls:true},"SECOND_LOOK_REQUIRED");
check("personalization missing",f=>f.m.personalization="","PERSONALIZATION_REQUIRED");
function sent(f,at=now) { f.s.events.push({recipient_key:f.m.to,account_id:f.m.account_id,delivery:"SENT",sent_at:at,message_id:"synthetic-sent"}); }
check("duplicate recipient different account",f=>{sent(f);f.s.events[0].account_id="different";},"ALREADY_CONTACTED");
check("account alias recipient",f=>{sent(f);f.s.events[0].recipient_key="alias@example.com";},"ALREADY_CONTACTED");
check("unresolved transport",f=>{sent(f);f.s.events[0].delivery="UNKNOWN";},"UNRESOLVED_PRIOR_SEND");
check("early follow up",f=>{sent(f);f.m.touch=2;f.m.reply_to_message_id="synthetic-sent";},"FOLLOW_UP_NOT_DUE");
check("valid day 5",f=>{sent(f,"2026-10-03T20:30:00Z");f.m.touch=2;f.m.reply_to_message_id="synthetic-sent";},null);
check("follow up after reply",f=>{sent(f,"2026-10-03T20:30:00Z");f.m.touch=2;f.m.reply_to_message_id="synthetic-sent";f.s.contacts[0].status="REPLIED";},"STOP_SEQUENCE_ON_REPLY");
check("follow up no thread",f=>{sent(f,"2026-10-03T20:30:00Z");f.m.touch=2;},"PRIOR_THREAD_REQUIRED");
check("draft not send",f=>{sent(f);f.s.events[0].delivery="DRAFT";},null);
check("unknown scale score",f=>f.s.contacts[0].qualification={...q,score:undefined},"ICP_QUALIFICATION_REQUIRED");
check("unknown history",f=>f.s.contacts[0].qualification={...q,history_months:undefined},"ICP_QUALIFICATION_REQUIRED");
check("hidden HTML footer",f=>f.m.html='<p style="display:none">'+f.m.text+'</p>',"HTML_HIDDEN_CONTENT");
const f=fixture(), p=approvalFor(f.m), r=reserveOutreach(f.m,f.s,f.a,p,now,"atomic-first");
assert(r.ok && f.s.events.length===0,"input immutable");
const changed={...f.m,to:"BUYER@EXAMPLE.COM"};
const p2={...approvalFor(changed),approval_id:"atomic-second-approval"};
const r2=reserveOutreach(changed,r.state,f.a,p2,now,"atomic-second");
assert(!r2.ok && r2.errors.includes("UNRESOLVED_PRIOR_SEND"),"second worker/batch reservation blocked"); count++;
assert(recipientKey("User.Name+campaign@googlemail.com")==="username@gmail.com","Gmail aliases"); count++;
assert(recipientKey("a.b+tag@example.com")==="a.b+tag@example.com","corporate aliases preserved"); count++;
console.log(count+" outreach safeguard checks passed");
