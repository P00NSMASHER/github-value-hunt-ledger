// Static private owner UI; no customer data is inserted into HTML or a public asset.
import {visualStyle} from './retally_os_visual.mjs';
import {visualScript} from './retally_os_ux.mjs';
// All dynamic values are assigned via textContent or form.value, never innerHTML.
const style=String.raw`
:root{color-scheme:dark;--bg:#071321;--card:#102238;--edge:#294059;--text:#eaf2f8;--muted:#91a9bc;--teal:#64d2bc;--gold:#e7ba71;--red:#ff959e;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(150deg,#071321,#0b1c2c 60%,#112535);color:var(--text);min-height:100vh}
button,input,select,textarea{font:inherit}button{cursor:pointer;background:#1b364a;color:var(--text);border:1px solid var(--edge);border-radius:10px;padding:10px 14px}button:hover{border-color:var(--teal)}button.primary{background:var(--teal);color:#062126;font-weight:750}button:disabled{opacity:.5;cursor:not-allowed}
a{color:var(--teal)}header{position:sticky;top:0;z-index:10;display:flex;justify-content:space-between;align-items:center;gap:12px;background:#091827f2;border-bottom:1px solid var(--edge);padding:14px max(20px,calc((100vw - 1160px)/2));backdrop-filter:blur(10px)}
.brand{display:flex;flex-direction:column;line-height:1.1;letter-spacing:.12em;font-size:22px;font-weight:900}.brand small{color:var(--teal);font-size:9px;font-weight:750;letter-spacing:.25em;margin-top:5px}.right{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted)}
main{max-width:1160px;margin:auto;padding:24px 18px 100px}h1{font-size:clamp(27px,4vw,44px);margin:6px 0 8px;letter-spacing:-.04em}h2{font-size:23px;margin:6px 0 12px}p{line-height:1.5}small,.muted{color:var(--muted)}.eyebrow{color:var(--gold);font-size:11px;font-weight:750;letter-spacing:.19em}.lead{color:var(--muted);max-width:700px;margin:0 0 25px}
nav{display:flex;gap:6px;overflow-x:auto;padding:6px 0 17px;margin:8px 0 20px;border-bottom:1px solid var(--edge)}nav button{flex:0 0 auto;white-space:nowrap;background:transparent;border-color:transparent;font-weight:600}nav button.active{color:var(--teal);border-color:var(--teal);background:#14313d}
.panel{display:none}.panel.active{display:block}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0}.tile,.box,.case,.draft{border:1px solid var(--edge);background:var(--card);border-radius:14px;padding:18px;box-shadow:0 7px 24px #0002}.tile strong{display:block;font-size:clamp(23px,3vw,35px);margin:9px 0;color:var(--text);font-variant-numeric:tabular-nums}.tile .label{color:var(--muted);font-size:12px}
.two{display:grid;grid-template-columns:1.5fr 1fr;gap:14px}.stack{display:grid;gap:13px}.case h3,.draft h3{margin:0 0 5px;font-size:17px}.case header,.draft header{position:static;background:transparent;border:0;padding:0;backdrop-filter:none}.case .meta{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;font-size:12px;color:var(--muted)}.tag{border:1px solid var(--edge);border-radius:999px;padding:3px 8px;font-size:11px;color:var(--muted)}.tag.verified{color:var(--teal);border-color:#276f63}.tag.test{color:var(--gold);border-color:#886a33}
.controls{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.controls label,.field{display:grid;gap:5px;font-size:11px;color:var(--muted)}input,select,textarea{width:100%;background:#081829;border:1px solid var(--edge);color:var(--text);border-radius:8px;padding:11px;outline:none}input:focus,select:focus,textarea:focus{border-color:var(--teal)}textarea{min-height:72px;resize:vertical}.case .save{margin-top:9px}.case .extra{margin-top:10px}.draft{display:grid;gap:9px}.draft .controls{grid-template-columns:1fr 1fr}.draft p{white-space:pre-wrap;margin:0;color:#d0dfeb}.actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.empty{border:1px dashed var(--edge);border-radius:12px;padding:22px;color:var(--muted)}.banner{border-left:3px solid var(--gold);padding:12px 15px;background:#2a271d;color:#f2e4ce;border-radius:8px}.ok{color:var(--teal)}.error{color:var(--red)}.hidden{display:none!important}#flash{position:sticky;top:70px;z-index:12;padding:9px 12px;border-radius:9px;background:#142d32;border:1px solid var(--teal);display:none;margin-bottom:12px}#flash.error{border-color:var(--red);background:#301b27}.toolline{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:15px 0}#search{max-width:420px}footer{font-size:12px;color:var(--muted);margin-top:32px;border-top:1px solid var(--edge);padding-top:18px}
@media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.two{grid-template-columns:1fr}.controls{grid-template-columns:1fr 1fr}header{padding:12px 15px}.right span{display:none}}
@media(max-width:460px){.grid{gap:9px}.tile,.box,.case,.draft{padding:14px}.tile strong{font-size:27px}.controls,.draft .controls{grid-template-columns:1fr}main{padding:18px 12px 80px}nav button{font-size:12px;padding:9px 11px}}
`;
const script=String.raw`
'use strict';
const base=location.pathname;const byId=id=>document.getElementById(id);let current=null;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n}
function add(parent,...children){for(const c of children)parent.append(c);return parent}
function clear(node){while(node.firstChild)node.firstChild.remove()}
function flash(message,bad=false){const n=byId('flash');n.textContent=message;n.className=bad?'error':'';n.style.display='block';window.scrollTo({top:0,behavior:'smooth'})}
function show(tab){document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));}
async function api(payload){const r=await fetch(base,{method:'POST',credentials:'same-origin',redirect:'error',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||('HTTP '+r.status));return data;}
async function refresh(){try{const r=await fetch(base+'?view=data',{credentials:'same-origin',redirect:'error',cache:'no-store',headers:{'Accept':'application/json'}});if(!r.ok)throw Error('Private read failed (HTTP '+r.status+'). Sign in again.');current=await r.json();render();byId('updated').textContent='Checked '+new Date(current.observedAt).toLocaleString();}catch(e){flash(e.message,true)}}
function tile(label,value){return add(el('article',undefined,'tile'),el('span',label,'label'),el('strong',value))}
function todayDate(){const now=new Date();return new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,10)}
function drawToday(){
 const t=byId('metrics');clear(t);const cases=current.cases||[];const tasks=(current.tasks||[]).filter(x=>!x.synthetic);
 const due=todayDate();const open=tasks.filter(x=>x.status==='open');const overdue=open.filter(x=>x.dueOn&&x.dueOn<due);
 add(t,tile('Latest inquiries',cases.length),tile('Non-test inquiries',cases.filter(c=>!c.synthetic).length),
  tile('Cases needing review',cases.filter(c=>!c.synthetic&&(!c.status||c.status==='reviewing'||c.status==='on_hold')).length),
  tile('Open follow-ups',open.length),tile('Overdue follow-ups',overdue.length),tile('Private social drafts',current.drafts.length));
 const n=byId('recent');clear(n);for(const c of cases.filter(c=>!c.synthetic).slice(0,8))n.append(caseCard(c,false));
 if(!n.childNodes.length)n.append(el('p','No genuine inquiry is present in the latest received data. QA records are excluded from genuine customer counts.','empty'));
 const urgent=byId('urgent');clear(urgent);
 for(const x of overdue.slice(0,5))urgent.append(el('p',x.dueOn+' · '+x.title+' · '+x.owner,'error'));
 if(!overdue.length)urgent.append(el('p','No overdue non-test follow-ups in the returned tasks.','muted'));
}

function field(label,value,type='text'){const wrap=el('label',undefined,'field');const name=el('span',label);const input=document.createElement('input');input.type=type;input.value=value||'';input.maxLength=type==='date'?10:80;add(wrap,name,input);return {wrap,input};}
function dropdown(label,values,selected){const l=el('label',undefined,'field');l.append(el('span',label));const s=document.createElement('select');for(const [v,text] of values){const o=el('option',text);o.value=v;if(v===selected)o.selected=true;s.append(o)}l.append(s);return {wrap:l,input:s}}
function caseCard(c,editor=true){const card=el('article',undefined,'case');card.dataset.ref=c.reference;const title=add(el('h3'),document.createTextNode(c.company||'(Company unavailable)'));const tag=el('span',c.synthetic?'TEST RECORD':'INBOUND',c.synthetic?'tag test':'tag verified');const head=add(el('div'),title,tag);add(card,head,el('div',c.reference+' · '+c.service+' · '+new Date(c.acceptedAt*1000).toLocaleString(),'meta'));
add(card,el('div',c.contact||'Contact unavailable','muted'));if(c.email){const email=el('div',c.email,'muted');card.append(email)}
const details=el('div',undefined,'meta');add(details,el('span','Status: '+(c.status||'new')),el('span','Notification: '+c.notification));card.append(details);
if(!editor)return card;
const owner=field('Assigned to',c.owner||'Owner');const due=field('Follow-up date',c.dueOn||'','date');const status=dropdown('Case status',[['reviewing','Reviewing'],['qualified','Qualified (manual assessment)'],['on_hold','On hold'],['closed','Closed (no cash claim)']],c.status||'reviewing');const fields=add(el('div',undefined,'controls'),owner.wrap,due.wrap,status.wrap);card.append(fields);
const memo=el('label',undefined,'field extra');add(memo,el('span','Internal case note (never sent)'),(()=>{const n=document.createElement('textarea');n.value=c.note||'';n.maxLength=1000;return n})());card.append(memo);
const b=el('button','Save case','primary save');b.addEventListener('click',async()=>{b.disabled=true;try{await api({action:'save_case',reference:c.reference,expectedVersion:c.version||0,owner:owner.input.value,dueOn:due.input.value,status:status.input.value,note:memo.querySelector('textarea').value});await refresh();flash('Private case updated. No external message was sent.')}catch(e){flash(e.message,true)}finally{b.disabled=false}});card.append(b);return card;}
function drawCases(){const root=byId('case-list');clear(root);const q=byId('search').value.trim().toLowerCase();const cases=current.cases.filter(c=>[c.reference,c.company,c.contact,c.owner,c.email].some(x=>String(x||'').toLowerCase().includes(q)));for(const c of cases)root.append(caseCard(c));if(!cases.length)root.append(el('p','No matching case.','empty'));byId('case-count').textContent=cases.length+' shown · latest 100 only';}
function taskCard(t){
 const card=el('article',undefined,'case');const parent=current.cases.find(c=>c.reference===t.reference);
 card.append(el('h3',t.title));
 card.append(el('p',t.reference+' · '+(parent?.company||'Existing inquiry')+(t.synthetic?' · QA TEST':''),'muted'));
 const status=dropdown('Status',[['open','Open'],['done','Completed'],['cancelled','Cancelled']],t.status);
 const due=field('Due date',t.dueOn||'','date');const owner=field('Responsible',t.owner);
 card.append(add(el('div',undefined,'controls'),owner.wrap,due.wrap,status.wrap));
 const note=el('label',undefined,'field extra');const memo=document.createElement('textarea');
 memo.value=t.note||'';memo.maxLength=1000;add(note,el('span','Private follow-up note (explain completion or cancellation)'),memo);card.append(note);
 const save=el('button','Save follow-up','save');save.addEventListener('click',async()=>{
  save.disabled=true;try{await api({action:'save_task',taskId:t.taskId,reference:t.reference,expectedVersion:t.version,
   title:t.title,owner:owner.input.value,dueOn:due.input.value,status:status.input.value,note:memo.value});
   await refresh();flash('Follow-up saved privately. No customer message was sent.');
  }catch(e){flash(e.message,true)}finally{save.disabled=false}
 });card.append(add(el('div',undefined,'actions'),save,el('small','Version '+t.version+' · '+new Date(t.updatedAt*1000).toLocaleString())));return card;
}
function drawTasks(){
 const selector=byId('task-reference');const prior=selector.value;clear(selector);
 for(const c of current.cases){const option=el('option',c.reference+' · '+c.company+(c.synthetic?' [TEST]':''));option.value=c.reference;selector.append(option)}
 if(current.cases.some(c=>c.reference===prior))selector.value=prior;
 const tasks=current.tasks||[];const root=byId('task-list');clear(root);
 for(const t of tasks)root.append(taskCard(t));
 if(!tasks.length)root.append(el('p','No follow-ups yet. Create a private task against an accepted inquiry.','empty'));
 byId('task-count').textContent=tasks.filter(t=>t.status==='open').length+' open · '+tasks.length+' returned (maximum 200)';
 byId('new-task').disabled=!current.cases.length;
}
function drawDrafts(){const root=byId('drafts');clear(root);for(const d of current.drafts){const card=el('article',undefined,'draft');const title=field('Title',d.title);title.input.maxLength=100;const channel=dropdown('Platform (not connected)',[['linkedin','LinkedIn'],['facebook','Facebook'],['instagram','Instagram'],['x','X']],d.channel);const head=add(el('div',undefined,'controls'),title.wrap,channel.wrap);card.append(head);const memo=el('label',undefined,'field');memo.append(el('span','Private draft content'));const body=document.createElement('textarea');body.value=d.body;body.maxLength=1800;memo.append(body);card.append(memo);card.append(el('span','State: '+d.status+' · version '+d.version,'tag'));
const actions=el('div',undefined,'actions');const save=el('button','Save revision');save.addEventListener('click',async()=>{try{await api({action:'save_draft',draftId:d.draftId,expectedVersion:d.version,title:title.input.value,channel:channel.input.value,body:body.value});await refresh();flash('Saved locally. Previous review cleared; no post published.')}catch(e){flash(e.message,true)}});actions.append(save);
const approve=el('button','Mark reviewed');approve.disabled=d.status==='reviewed';approve.addEventListener('click',async()=>{try{await api({action:'review_draft',draftId:d.draftId,expectedVersion:d.version});await refresh();flash('Review recorded. Publication remains disabled.')}catch(e){flash(e.message,true)}});actions.append(approve);card.append(actions);root.append(card)}if(!current.drafts.length)root.append(el('p','No private drafts yet. Use New draft to begin. Postmill is not a live publishing connection.','empty'));}
function drawGrowth(){const n=byId('channels');clear(n);const map=new Map();for(const c of current.cases){if(c.synthetic)continue;const key=c.campaign?.utm_source||'direct/unknown';map.set(key,(map.get(key)||0)+1)}for(const [key,count] of map)n.append(add(el('article',undefined,'box'),el('strong',key),el('p',count+' inbound inquiry record(s); not an attributed sale.')));if(!map.size)n.append(el('p','No non-test campaign attribution is available.','empty'))}
function render(){drawToday();drawCases();drawTasks();drawDrafts();drawGrowth();byId('latest').textContent='Source: RETALLY D1 · latest '+current.cases.length+' recorded inquiries';byId('ops-read').textContent='Live intake: read-only · case notes: private D1 · social publishing: disabled';}
byId('search').addEventListener('input',()=>{if(current)drawCases()});document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>show(b.dataset.tab)));
byId('refresh').addEventListener('click',refresh);
byId('new-task').addEventListener('click',async()=>{
 const b=byId('new-task'),reference=byId('task-reference').value,title=byId('task-title'),owner=byId('task-owner'),due=byId('task-due'),note=byId('task-note');
 b.disabled=true;try{await api({action:'save_task',taskId:crypto.randomUUID(),reference,expectedVersion:0,
  title:title.value,owner:owner.value,dueOn:due.value,status:'open',note:note.value});
  title.value='';note.value='';await refresh();flash('Follow-up created privately. No email or posting.');
 }catch(e){flash(e.message,true)}finally{b.disabled=false}
});
byId('new-draft').addEventListener('click',async()=>{const title=byId('draft-title'),body=byId('draft-body'),channel=byId('draft-channel');try{await api({action:'save_draft',draftId:crypto.randomUUID(),expectedVersion:0,title:title.value,body:body.value,channel:channel.value});title.value='';body.value='';await refresh();flash('Draft stored privately. No publication or scheduling.')}catch(e){flash(e.message,true)}});
refresh();
`;
export function renderRetallyOsPage(nonce) {
  const html=String.raw`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#071321"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="RETALLY OS"><title>RETALLY OS | Private</title><style nonce="__NONCE__">__STYLE__</style></head><body>
<header><div class="brand"><span class="brand-emblem" aria-hidden="true">R</span><span class="brand-copy">RETALLY<small>OPERATING SYSTEM</small></span></div><div class="right"><span class="secure-label">PRIVATE WORKSPACE</span><button id="refresh" type="button">↻ Refresh</button><a class="header-link" href="/cdn-cgi/access/logout">Sign out</a></div></header>
<main>
<div id="flash" role="status" aria-live="polite"></div>
<div class="page-heading">
 <div><div class="eyebrow" id="view-kicker">OPERATIONS / TODAY</div><h1 id="view-title">Your business at a glance</h1><p class="lead" id="view-description">A clear view of inquiries, priorities and work that needs attention.</p></div>
 <div class="sync-indicator" aria-live="polite"><span class="sync-dot" id="sync-dot" aria-hidden="true"></span><span id="sync-time">Connecting to private data…</span></div>
</div>
<nav aria-label="Workspace tabs">
<div class="sidebar-section">WORKSPACE</div>
<button class="active" data-tab="today" aria-current="page" type="button"><span class="nav-icon" aria-hidden="true">01</span> Overview</button>
<button data-tab="cases" type="button"><span class="nav-icon" aria-hidden="true">02</span> Customers &amp; cases</button>
<button data-tab="tasks" type="button"><span class="nav-icon" aria-hidden="true">03</span> Follow-ups</button>
<button data-tab="social" type="button"><span class="nav-icon" aria-hidden="true">04</span> Social drafts</button>
<div class="sidebar-section">INTELLIGENCE</div>
<button data-tab="growth" type="button"><span class="nav-icon" aria-hidden="true">05</span> Growth</button>
<button data-tab="finance" type="button"><span class="nav-icon" aria-hidden="true">06</span> Financials</button>
<button data-tab="ops" type="button"><span class="nav-icon" aria-hidden="true">07</span> System status</button>
<div class="sidebar-footer">● Owner-only workspace<br>Private D1 records · No automated outbound actions</div>
</nav>
<section class="panel active" data-tab="today">
<div class="section-head"><h2>Today's overview</h2><span class="section-overline">REAL SIGNALS · NO TEST INFLATION</span></div>
<div id="metrics" class="grid" aria-label="Business metrics"></div>
<div class="two">
 <div><div class="section-head"><h2>Recent real inquiries</h2><button type="button" class="mini-link" id="see-cases">View pipeline →</button></div><div class="stack" id="recent"></div></div>
 <div><div class="section-head"><h2>Recommended next actions</h2></div><article class="box"><div id="urgent"></div><div class="banner">Customer and revenue figures exclude QA records. Actions here are private; no messages or posts are sent.</div></article></div>
</div>
</section>
<section class="panel" data-tab="cases">
<div class="section-head"><h2>Case pipeline</h2><span class="section-overline">ORIGINAL INQUIRY RECEIPTS · READ-ONLY</span></div>
<p class="muted">Work each accepted inquiry, keep private notes and track ownership. Original submission records are never edited.</p>
<div class="toolline"><input type="search" id="search" aria-label="Search cases" placeholder="Search company, reference, contact…" maxlength="100"><small id="case-count"></small></div>
<div id="case-filters" class="filter-strip" aria-label="Filter cases">
<button type="button" class="active" data-filter="live" aria-pressed="true">Genuine inquiries</button><button type="button" data-filter="review" aria-pressed="false">Needs review</button><button type="button" data-filter="test" aria-pressed="false">QA records</button><button type="button" data-filter="all" aria-pressed="false">All records</button>
</div><div id="case-list" class="stack"></div>
</section>
<section class="panel" data-tab="tasks">
<div class="section-head"><h2>Follow-ups &amp; owner tasks</h2><span class="section-overline">PRIVATE WORK QUEUE</span></div>
<p class="muted">Tasks are linked to accepted inquiries and kept in your private records. Completing or cancelling requires a written note.</p>
<div class="two">
 <article class="box"><h3>Create a follow-up</h3><p class="muted">Assign one clear next action with a due date.</p>
  <div class="stack">
   <label class="field">Accepted inquiry<select id="task-reference"></select></label>
   <label class="field">What needs doing?<input id="task-title" maxlength="140" placeholder="Review invoice documents"></label>
   <div class="controls"><label class="field">Owner<input id="task-owner" maxlength="80" value="Owner"></label><label class="field">Due date<input id="task-due" type="date"></label></div>
   <label class="field">Internal note<textarea id="task-note" maxlength="1000" placeholder="Context for your next step (private)"></textarea></label>
   <button type="button" id="new-task" class="primary">Create follow-up</button>
  </div>
 </article>
 <article class="box"><h3>How this queue works</h3>
  <div class="priority-row"><span class="priority-number" aria-hidden="true">01</span><div><strong>Track a clear action</strong><small>Choose the case, owner and due date.</small></div></div>
  <div class="priority-row"><span class="priority-number" aria-hidden="true">02</span><div><strong>Update the record</strong><small>Mark work done or cancelled with a reason.</small></div></div>
  <div class="priority-row"><span class="priority-number" aria-hidden="true">03</span><div><strong>Keep work private</strong><small>No customer email, social post or payment is triggered.</small></div></div>
  <p id="task-count" class="muted"></p>
 </article>
</div>
<div class="section-head"><h2>Saved follow-ups</h2><span class="section-overline">SAVED VERSIONS · CONFLICT SAFE</span></div>
<div id="task-filters" class="filter-strip" aria-label="Filter follow-ups">
<button type="button" class="active" data-filter="open" aria-pressed="true">Open</button><button type="button" data-filter="overdue" aria-pressed="false">Overdue</button><button type="button" data-filter="done" aria-pressed="false">Completed</button><button type="button" data-filter="test" aria-pressed="false">QA tasks</button><button type="button" data-filter="all" aria-pressed="false">All</button>
</div>
<div id="task-list" class="stack"></div>
</section>
<section class="panel" data-tab="social">
<div class="section-head"><h2>Content studio</h2><span class="section-overline">EDITORIAL / PRIVATE ONLY</span></div>
<div class="banner"><strong>Private drafts, not scheduled posts.</strong> Review does not publish. Postmill is an isolated pilot; the existing Metricool planner is separate.</div>
<p><a href="https://app.metricool.com/planner/calendar?blogId=7322512" target="_blank" rel="noreferrer noopener">Open the connected RETALLY Metricool planner →</a></p>
<div class="two"><article class="box"><h3>New private draft</h3><p class="muted">Prepare an idea and review the language before any separate publishing decision.</p>
 <div class="stack"><label class="field">Title<input id="draft-title" maxlength="100" placeholder="Audit opportunity explained"></label>
 <label class="field">Channel<select id="draft-channel"><option value="linkedin">LinkedIn</option><option value="facebook">Facebook</option><option value="instagram">Instagram</option><option value="x">X</option></select></label>
 <label class="field">Draft copy<textarea id="draft-body" maxlength="1800" placeholder="Write the post for internal review…"></textarea></label>
 <button type="button" id="new-draft" class="primary">Save private draft</button></div></article>
 <article class="box"><h3>Editorial workflow</h3><div class="priority-row"><span class="priority-number" aria-hidden="true">01</span><div><strong>Draft</strong><small>Save content to private RETALLY D1.</small></div></div><div class="priority-row"><span class="priority-number" aria-hidden="true">02</span><div><strong>Review</strong><small>Mark a version reviewed; editing clears review.</small></div></div><div class="priority-row"><span class="priority-number" aria-hidden="true">03</span><div><strong>Publish separately</strong><small>No publish action is available in this dashboard.</small></div></div></article>
</div>
<div class="section-head"><h2>Saved drafts</h2></div><div id="drafts" class="stack"></div>
</section>
<section class="panel" data-tab="growth">
<div class="section-head"><h2>Where inquiries come from</h2><span class="section-overline">ACTUAL FORM ATTRIBUTION</span></div>
<p class="muted">Only genuine submissions are counted. These source tags do not measure reach, revenue or conversions.</p>
<div id="channels" class="stack"></div>
</section>
<section class="panel" data-tab="finance">
<div class="section-head"><h2>Money, with evidence</h2><span class="section-overline">NO ESTIMATES AS REVENUE</span></div>
<div class="grid finance-grid"><div class="tile"><span class="label">Verified cash received</span><strong>Unknown</strong><span class="kpi-detail">No payments source connected</span></div><div class="tile"><span class="label">Verified paying customers</span><strong>Unknown</strong><span class="kpi-detail">No verified payment evidence</span></div></div>
<div class="banner">This view does not infer payments from case status, projected recovery, CRM notes or pilot amounts. Cash remains unknown until an independent receipt is connected.</div>
</section>
<section class="panel" data-tab="ops">
<div class="section-head"><h2>Connection &amp; security</h2><span class="section-overline">OPERATOR READOUT</span></div>
<div class="box system-lines">
<p id="latest"></p><p id="ops-read"></p><p><strong>Identity:</strong> Cloudflare Access with independently checked owner JWT. Preview hosts cannot access customer records.</p><p><strong>Not connected:</strong> GopherCRM, Postmill and Prime Agent are private tested pilots, not deployed production services.</p><p><strong>Publish and payments:</strong> Disabled from RETALLY OS.</p><p id="updated" class="muted"></p>
</div></section>
<footer>RETALLY · Find it. Prove it. Recover it. · Owner-only · No automatic outbound actions</footer></main><div id="more-sheet" class="more-sheet" aria-label="More sections"><h3>More sections</h3><button type="button" data-more-tab="growth">05 · Growth insights</button><button type="button" data-more-tab="finance">06 · Financials</button><button type="button" data-more-tab="ops">07 · System status</button><a class="header-link" href="/cdn-cgi/access/logout">Sign out</a></div>
<div id="mobile-dock" class="mobile-dock" role="navigation" aria-label="Mobile navigation">
 <button type="button" data-tab="today" class="active" aria-current="page"><span class="dock-icon" aria-hidden="true">⌂</span>Overview</button>
 <button type="button" data-tab="cases"><span class="dock-icon" aria-hidden="true">▤</span>Cases</button>
 <button type="button" data-tab="tasks"><span class="dock-icon" aria-hidden="true">✓</span>Tasks</button>
 <button type="button" data-tab="social"><span class="dock-icon" aria-hidden="true">✎</span>Content</button>
 <button type="button" id="more-toggle" aria-expanded="false" aria-controls="more-sheet"><span class="dock-icon" aria-hidden="true">···</span>More</button>
</div><script nonce="__NONCE__">__SCRIPT__</script></body></html>`;
  const upgradedScript=script.replace(/\nrefresh\(\);\n$/, '\n'+visualScript+'\nrefresh();\n');
  if (upgradedScript===script) throw new Error('RETALLY UI startup hook unavailable');
  return html.replaceAll('__NONCE__',nonce).replace('__STYLE__',style+'\n'+visualStyle).replace('__SCRIPT__',upgradedScript);
}
