'use strict';
let credential = '', state = null, uploadText = '', uploadMapping = {};
const $ = id => document.getElementById(id);
const money = (cents, currency) => new Intl.NumberFormat('en-US', {style:'currency',currency,currencyDisplay:'code'}).format(cents/100);
const node = (tag, text, cls) => { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; };
async function api(path, data) {
  const response = await fetch('/api/'+path, {method:data===undefined?'GET':'POST', headers:{'Authorization':'Bearer '+credential, 'Content-Type':'application/json'}, ...(data===undefined?{}:{body:JSON.stringify(data)})});
  const result=await response.json(); if(!response.ok)throw new Error(result.error || 'Request failed'); return result;
}
async function guard(work) { $('error').textContent=''; $('login-error').textContent=''; try {await work();}catch(e){$('error').textContent=e.message;$('login-error').textContent=$('workspace').hidden?e.message:'';} }
function button(text, action) { const b=node('button',text);b.type='button';b.addEventListener('click',()=>guard(action));return b; }
function field(form,label,type='text',value='') { const wrapper=node('label',label), input=node('input');input.type=type;input.value=value;input.required=true;wrapper.append(input);form.append(wrapper);return input; }
async function refresh() {
 state=await api('state');$('login').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;
 $('mode').textContent=state.simulation?'SIMULATION — Synthetic customers, reviewers and money. No live recoveries or approvals.':'PRIVATE PILOT — Evidence and approvals require authorized people. External actions use the controlled workflow.';
 $('client').textContent=state.client_id;$('actor').textContent=state.actor.role.toUpperCase();
 const currencies=[...new Set(state.cases.map(c=>c.currency))].sort();
 const metrics=[];
 for(const currency of currencies){
  const cases=state.cases.filter(c=>c.currency===currency), active=cases.filter(c=>!c.hold&&c.state!=='REJECTED');
  const totals=[['Recorded potential',cases.reduce((a,c)=>a+c.potential_cents,0)],['Available for review',active.reduce((a,c)=>a+c.remaining_cents,0)],['Net received',cases.reduce((a,c)=>a+c.recovered_cents,0)],['Net fees',cases.reduce((a,c)=>a+c.fee_cents,0)]];
  for(const [label,value] of totals){const e=node('div',undefined,'metric');e.append(node('span',label),node('strong',money(value,currency)));metrics.push(e);}
 }
 $('metrics').replaceChildren(...metrics);
 renderCases();renderSources();
 const selected=$('branch').value;$('branch').replaceChildren(...Object.keys(state.schemas).map(b=>{const e=node('option',b);e.value=b;return e;}));if(selected)$('branch').value=selected;setSources();
 $('upload-form').hidden=!['customer','operator'].includes(state.actor.role);$('settings-form').hidden=state.actor.role!=='operator';$('scan').disabled=state.actor.role!=='operator';$('backup').disabled=state.actor.role!=='operator';
}
function renderCases(){
 $('case-list').replaceChildren();if(!state.cases.length)$('case-list').append(node('p','No cases yet. Upload and review evidence, then run a scan.'));
 for(const c of state.cases){
 const detail=node('details',undefined,'case'),summary=node('summary');summary.append(node('span',c.branch.toUpperCase()+' · '+c.reference),node('span',money(c.potential_cents,c.currency)+' · '+(c.hold?'ON HOLD':c.state),'pill'+(c.hold?' hold':'')));detail.append(summary);
 detail.append(node('p',c.counterparty+' · Net received '+money(c.recovered_cents,c.currency)+' · Remaining '+money(c.remaining_cents,c.currency),'muted'));
 if(c.hold)detail.append(node('p',c.hold,'banner'));
 const evidence=node('div'); for(const e of c.evidence)evidence.append(node('p',e.kind+' · '+e.locator+' · SHA-256 '+e.sha256,'muted'));detail.append(evidence);
 const form=node('form'); const note=field(form,'Review / authorization note'); const controls=node('div',undefined,'actions');
 const documents=Object.values(state.documents).filter(d=>d.finding_id===c.finding_id), docInputs={};
 if(!state.simulation)for(const kind of ['case_bundle','authorization','external_action','cash_event']){const label=node('label','Reviewed '+kind.replaceAll('_',' ')),select=node('select');select.append(node('option','Select reviewed document'));select.firstChild.value='';for(const d of documents.filter(d=>d.kind===kind&&d.review)){const option=node('option',d.id.slice(0,12));option.value=d.id;select.append(option);}label.append(select);form.append(label);docInputs[kind]=select;}
 const documentData=action=>state.simulation?{}:{bundle_document_id:docInputs.case_bundle.value,authorization_document_id:docInputs.authorization.value,document_id:(action==='cash'?docInputs.cash_event:docInputs.external_action).value};
 const act=async(action,data={})=>{await api('action',{action,finding_id:c.finding_id,expected_head:state.head_hash,data:{note:note.value,...documentData(action),...data}});await refresh();};
 if(state.actor.role==='reviewer'){controls.append(button('Approve evidence',()=>act('approve')),button('Place reconciliation hold',()=>act('hold')));}
 if(state.actor.role==='independent'){controls.append(button('Independent approval',()=>act('independent')));if(c.hold){const hash=field(form,'Reconciliation evidence SHA-256');controls.append(button('Retain proof and release hold',()=>act('resolve',{evidence_hash:hash.value,expected_record_hash:c.record_hash})));for(const conflict of state.conflicts.filter(x=>x.existing_finding_id===c.finding_id)){const replacement=conflict.replacement;controls.append(button('Replace with corrected case '+replacement.finding_id.slice(-8),()=>act('revise',{evidence_hash:hash.value,expected_record_hash:c.record_hash,replacement_id:replacement.finding_id})));}}}
 if(state.actor.role==='customer')controls.append(button('Authorize this case',()=>act('authorize')));
 if(state.actor.role==='operator'&&state.simulation){controls.append(button('Simulate claim submission',()=>act('claim')));const id=field(form,'Receipt / reversal ID'),amount=field(form,'Amount in cents (negative for reversal)','number'),fee=field(form,'Fee in cents','number','0'),hash=field(form,'Simulated receipt SHA-256'),reverse=field(form,'Original receipt ID (reversals only)');reverse.required=false;controls.append(button('Post simulated receipt',()=>act('cash',{event_id:id.value,amount_cents:Number(amount.value),fee_cents:Number(fee.value),source_hash:hash.value,reverses_id:reverse.value||null})));}
 if(state.actor.role==='operator'&&!state.simulation)controls.append(button('Record reviewed external submission',()=>act('claim')),button('Post reviewed receipt / reversal',()=>act('cash')));
 form.addEventListener('submit',e=>e.preventDefault());form.append(controls);detail.append(form);
 const kinds={customer:['authorization'],reviewer:['case_bundle'],independent:['case_bundle'],operator:['external_action','cash_event']}[state.actor.role];
 const attachment=node('form'),kindLabel=node('label','Proof document'),kindSelect=node('select');for(const kind of kinds){const option=node('option',kind.replaceAll('_',' '));option.value=kind;kindSelect.append(option);}kindLabel.append(kindSelect);attachment.append(kindLabel);const file=field(attachment,'JSON evidence file','file');file.accept='.json';attachment.append(button('Upload case evidence',async()=>{if(!file.files[0])throw Error('Choose a JSON evidence file');await api('document',{finding_id:c.finding_id,kind:kindSelect.value,content:await file.files[0].text()});await refresh();}));attachment.addEventListener('submit',e=>e.preventDefault());detail.append(attachment);
 for(const d of documents){const box=node('div',undefined,'source'),preview=node('pre');box.append(node('strong',d.kind+' · '+(d.review?'reviewed':'awaiting review')),button('Read case document',async()=>{preview.textContent=(await api('source',{receipt_id:d.id})).content;}),preview);if(['reviewer','independent'].includes(state.actor.role)&&d.uploaded_by!==state.actor.actor_id){const reviewNote=field(box,'Document review note');box.append(button('Verify case document',async()=>{await api('review-document',{receipt_id:d.id,expected_sha256:d.normalized_sha256,note:reviewNote.value});await refresh();}));}detail.append(box);}
 $('case-list').append(detail);
 }
}
function renderSources(){
 $('source-list').replaceChildren();for(const record of Object.values(state.sources)){const e=node('div',undefined,'source');e.append(node('strong',record.branch+' / '+record.source),node('p',record.rows+' records · '+(record.review?'Reviewed':'Awaiting review'),'muted'),node('p','SHA-256 '+record.normalized_sha256,'muted'));
 if(['reviewer','independent'].includes(state.actor.role)){const form=node('form'),note=field(form,'Source review note');const preview=node('pre');form.append(button('Read uploaded evidence',async()=>{preview.textContent=(await api('source',{receipt_id:record.id})).content;}),preview);form.append(button('Verify exact source',async()=>{await api('review',{branch:record.branch,source:record.source,expected_sha256:record.normalized_sha256,note:note.value});await refresh();}));form.addEventListener('submit',event=>event.preventDefault());e.append(form);}$('source-list').append(e);}
}
function setSources(){const selected=$('source').value;$('source').replaceChildren(...Object.keys(state.schemas[$('branch').value]).map(s=>{const e=node('option',s);e.value=s;return e;}));if([...$('source').options].some(o=>o.value===selected))$('source').value=selected;uploadText='';uploadMapping={};$('file').value='';$('mapping').replaceChildren();}
$('branch').addEventListener('change',setSources);$('source').addEventListener('change',()=>{uploadText='';uploadMapping={};$('file').value='';$('mapping').replaceChildren();});
$('file').addEventListener('change',()=>guard(async()=>{const file=$('file').files[0];if(!file)return;if(file.size>5*1024*1024)throw Error('Maximum upload is 5 MiB');uploadText=await file.text();uploadMapping={};$('mapping').replaceChildren();const headers=state.schemas[$('branch').value][$('source').value][0];if(headers){const preview=await api('preview',{content:uploadText});for(const target of headers.split(',')){const label=node('label',target),select=node('select');for(const source of preview.columns){const option=node('option',source);option.value=source;select.append(option);}if(preview.columns.includes(target))select.value=target;uploadMapping[target]=select.value;select.addEventListener('change',()=>uploadMapping[target]=select.value);label.append(select);$('mapping').append(label);}}}));
$('upload-form').addEventListener('submit',e=>{e.preventDefault();guard(async()=>{await api('upload',{branch:$('branch').value,source:$('source').value,content:uploadText,mapping:uploadMapping});await refresh();});});
$('settings-form').addEventListener('submit',e=>{e.preventDefault();guard(async()=>{const branch=$('settings-branch').value,settings=branch==='rebate'?{as_of_date:$('effective').value}:{default_effective_from:$('effective').value};if(branch==='utility')settings.utility_id=$('utility').value;await api('settings',{branch,settings});$('operation-result').textContent='Scope settings saved.';});});
$('scan').addEventListener('click',()=>guard(async()=>{const result=await api('scan',{});$('operation-result').textContent=JSON.stringify(result,null,2);await refresh();}));
$('backup').addEventListener('click',()=>guard(async()=>{$('operation-result').textContent=JSON.stringify(await api('backup',{}),null,2);}));
$('login-form').addEventListener('submit',e=>{e.preventDefault();credential=$('token').value;$('token').value='';guard(refresh);});
$('logout').addEventListener('click',()=>{credential='';state=null;location.reload();});$('refresh').addEventListener('click',()=>guard(refresh));
for(const tab of document.querySelectorAll('[data-panel]'))tab.addEventListener('click',()=>{for(const p of document.querySelectorAll('.panel'))p.hidden=p.id!==tab.dataset.panel;for(const b of document.querySelectorAll('[data-panel]'))b.classList.toggle('active',b===tab);});
