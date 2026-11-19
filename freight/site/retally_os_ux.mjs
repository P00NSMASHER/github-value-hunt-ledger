/* Interactive presentation-only layer. Existing private D1 endpoints stay unchanged. */
export const visualScript = String.raw`// RETALLY OS user-experience layer; runs inside the existing CSP-nonced private script.
// It does not request new endpoints, store credentials, or publish external content.
const viewBriefs={
 today:['OPERATIONS / TODAY','Your business at a glance','A clear view of inquiries, priorities and work that needs attention.'],
 cases:['RELATIONSHIPS / PIPELINE','Customers & cases','Review genuine inquiries, update case status and keep evidence organized.'],
 tasks:['EXECUTION / FOLLOW-UPS','The work queue','Track private tasks, due dates and completion history in one place.'],
 social:['MARKETING / EDITORIAL','Content studio','Draft and review privately. Nothing is published from this dashboard.'],
 growth:['INSIGHTS / ACQUISITION','Growth signals','See which tracked inquiry sources are actually represented in your data.'],
 finance:['FINANCE / EVIDENCE','Financial integrity','Claims and estimates are not payments. Only verified receipts count.'],
 ops:['SECURITY / SYSTEM','System status','Know what is connected, what is protected, and what is still a pilot.']
};
let activeCaseFilter='live';
let activeTaskFilter='open';
function setFilterButtons(id,currentFilter){
 for(const b of byId(id).querySelectorAll('button[data-filter]')){
  const on=b.dataset.filter===currentFilter;
  b.classList.toggle('active',on);
  b.setAttribute('aria-pressed',on?'true':'false');
 }
}
function emptyMessage(title,description,actionLabel,tab){
 const panel=el('div',undefined,'empty');
 add(panel,el('strong',title),el('span',description));
 if(actionLabel){
  const b=el('button',actionLabel,'mini-link');
  b.addEventListener('click',()=>show(tab));
  panel.append(b);
 }
 return panel;
}
function priorityRow(n,title,detail,buttonLabel,tab){
 const row=el('div',undefined,'priority-row');
 add(row,el('span',String(n).padStart(2,'0'),'priority-number'));
 const copy=el('div');
 add(copy,el('strong',title),el('small',detail));
 row.append(copy);
 if(buttonLabel){
  const button=el('button',buttonLabel);
  button.addEventListener('click',()=>show(tab));
  row.append(button);
 }
 return row;
}
function kpi(label,value,detail,tab,attention){
 const item=el('button',undefined,'tile'+(attention?' attention':''));
 item.type='button';
 item.setAttribute('aria-label',label+': '+value+'. '+detail+'. Open '+tab);
 add(item,el('span',label,'label'),el('strong',value),el('span',detail,'kpi-detail'));
 item.addEventListener('click',()=>show(tab));
 return item;
}
const originalShow=show;
show=function(tab){
 const target=document.querySelector('.panel[data-tab="'+tab+'"]');
 if(!target)return;
 originalShow(tab);
 for(const b of document.querySelectorAll('nav button[data-tab], .mobile-dock button[data-tab]')){
  const on=b.dataset.tab===tab;
  b.classList.toggle('active',on);
  if(on)b.setAttribute('aria-current','page');
  else b.removeAttribute('aria-current');
 }
 const more=['growth','finance','ops'].includes(tab);
 const m=byId('more-toggle');
 m.classList.toggle('active',more);
 m.setAttribute('aria-expanded','false');
 byId('more-sheet').classList.remove('open');
 const brief=viewBriefs[tab];
 byId('view-kicker').textContent=brief[0];
 byId('view-title').textContent=brief[1];
 byId('view-description').textContent=brief[2];
 window.scrollTo(0,0);
};
const originalCaseCard=caseCard;
caseCard=function(c,editor=true){
 const card=originalCaseCard(c,editor);
 card.classList.add('record-card');
 const h=card.querySelector('h3');
 const first=card.firstElementChild;
 if(first)first.classList.add('case-head');
 if(h)h.setAttribute('title',c.company||'Company unavailable');
 const statusText=c.status||'new';
 const status=el('span',statusText==='new'?'New inquiry':statusText.replaceAll('_',' '),'tag neutral');
 if(c.status==='on_hold')status.classList.add('danger');
 if(c.status==='qualified')status.classList.add('verified');
 const meta=card.querySelector('.meta');
 if(meta)meta.prepend(status);
 if(editor){
  const controls=card.querySelector('.controls');
  const note=card.querySelector('label.extra');
  const save=card.querySelector('button.save');
  if(controls&&note&&save){
   const details=el('details',undefined,'editor-disclosure');
   const summary=el('summary','Manage this case');
   details.append(summary,controls,note,save);
   card.append(details);
  }
 }
 return card;
};
function applyCaseFilters(){
 if(!current)return;
 const root=byId('case-list'),q=byId('search').value.trim().toLowerCase();
 let shown=0;
 for(const elCard of root.querySelectorAll('article[data-ref]')){
  const c=current.cases.find(x=>x.reference===elCard.dataset.ref);
  if(!c)continue;
  const match=[c.reference,c.company,c.contact,c.owner,c.email,c.service].some(x=>String(x||'').toLowerCase().includes(q));
  const status=c.status||'reviewing';
  const selected=activeCaseFilter==='all' || (activeCaseFilter==='test'&&c.synthetic) ||
    (activeCaseFilter==='live'&&!c.synthetic) ||
    (activeCaseFilter==='review'&&!c.synthetic&&['reviewing','on_hold'].includes(status));
  const visible=match&&selected;
  elCard.hidden=!visible;
  if(visible)shown++;
 }
 root.querySelectorAll('.no-filter-results').forEach(x=>x.remove());
 if(!shown){const empty=emptyMessage(activeCaseFilter==='test'?'No QA records match':'Nothing to show yet',activeCaseFilter==='test'?'Try clearing the search.':'Only accepted genuine inquiries appear in this view. Change the filter to see QA records.',null,null);empty.classList.add('no-filter-results');root.append(empty);}
 byId('case-count').textContent=shown+' shown · latest '+current.cases.length+' of up to 100';
 setFilterButtons('case-filters',activeCaseFilter);
}
const originalDrawCases=drawCases;
drawCases=function(){originalDrawCases();applyCaseFilters();};
const originalTaskCard=taskCard;
taskCard=function(t){
 const card=originalTaskCard(t);
 card.dataset.taskId=t.taskId;
 card.dataset.taskStatus=t.status;
 card.dataset.synthetic=t.synthetic?'1':'0';
 card.classList.toggle('is-done',t.status!=='open');
 const due=t.dueOn||'';
 const overdue=t.status==='open'&&due&&due<todayDate();
 if(overdue)card.classList.add('is-overdue');
 const heading=card.querySelector('h3');
 const badge=el('span',overdue?'Overdue':t.status==='done'?'Completed':t.status==='cancelled'?'Cancelled':t.synthetic?'QA test':!due?'No due date':due===todayDate()?'Due today':'Open',overdue?'tag danger':t.status==='done'?'tag verified':'tag neutral');
 if(heading){
  const top=el('div',undefined,'case-head');
  card.insertBefore(top,heading);
  top.append(heading,badge);
 }
 const controls=card.querySelector('.controls');
 const note=card.querySelector('label.extra');
 const actions=card.querySelector('.actions');
 if(controls&&note&&actions){
  const details=el('details',undefined,'editor-disclosure');
  details.append(el('summary','Update follow-up'),controls,note,actions);
  card.append(details);
 }
 return card;
};
function applyTaskFilters(){
 if(!current)return;
 const list=byId('task-list');
 const now=todayDate();
 let count=0;
 for(const card of list.querySelectorAll('article[data-task-id]')){
  const task=(current.tasks||[]).find(t=>t.taskId===card.dataset.taskId);
  if(!task)continue;
  const isOpen=task.status==='open',isTest=task.synthetic;
  const yes=activeTaskFilter==='all'||(activeTaskFilter==='test'&&isTest)||
    (activeTaskFilter==='open'&&isOpen&&!isTest)||
    (activeTaskFilter==='overdue'&&isOpen&&!isTest&&task.dueOn&&task.dueOn<now)||
    (activeTaskFilter==='done'&&!isOpen&&!isTest);
  card.hidden=!yes;
  if(yes)count++;
 }
 list.querySelectorAll('.no-filter-results').forEach(x=>x.remove());
 if(!count){const empty=emptyMessage('Your queue is clear','No follow-ups match this filter. Create one from an existing inquiry or switch views.',null,null);empty.classList.add('no-filter-results');list.append(empty);}
 byId('task-count').textContent=count+' shown · '+(current.tasks||[]).length+' returned (maximum 200)';
 setFilterButtons('task-filters',activeTaskFilter);
}
const originalDrawTasks=drawTasks;
drawTasks=function(){originalDrawTasks();applyTaskFilters();};
const originalDrawDrafts=drawDrafts;
drawDrafts=function(){
 originalDrawDrafts();
 for(const card of byId('drafts').querySelectorAll('.draft')){
  const header=card.querySelector('.controls');
  const body=card.querySelector(':scope > label.field');
  const state=card.querySelector('.tag');
  const actions=card.querySelector('.actions');
  if(!header||!body||!state||!actions)continue;
  const titleInput=header.querySelector('input');
  const preview=el('div',undefined,'case-head');
  const text=el('h3',titleInput?.value||'Untitled draft');
  add(preview,text,state);
  card.insertBefore(preview,header);
  const save=actions.querySelector('button');
  const details=el('details',undefined,'editor-disclosure');
  details.append(el('summary','Edit this draft'),header,body);
  if(save)details.append(save);
  card.append(details);
 }
};
const originalDrawToday=drawToday;
drawToday=function(){
 originalDrawToday();
 const cases=current.cases.filter(x=>!x.synthetic);
 const open=(current.tasks||[]).filter(x=>!x.synthetic&&x.status==='open');
 const overdue=open.filter(x=>x.dueOn&&x.dueOn<todayDate());
 const review=cases.filter(c=>!c.status||c.status==='reviewing'||c.status==='on_hold');
 const metrics=byId('metrics');clear(metrics);
 add(metrics,kpi('Genuine inquiries',cases.length,'QA submissions excluded','cases',false),
   kpi('Needs review',review.length,'Open the case pipeline','cases',review.length>0),
   kpi('Open follow-ups',open.length,'Review outstanding work','tasks',false),
   kpi('Overdue tasks',overdue.length,'Past the due date','tasks',overdue.length>0));
 const urgent=byId('urgent');clear(urgent);let priorityOrder=1;
 if(overdue.length)urgent.append(priorityRow(priorityOrder++,overdue.length+' overdue follow-up'+(overdue.length===1?'':'s'),'These have passed their saved due dates.','Review','tasks'));
 else if(review.length)urgent.append(priorityRow(priorityOrder++,review.length+' case'+(review.length===1?'':'s')+' need attention','Qualify a new inquiry or record the reason for a hold.','Open cases','cases'));
 else if(!cases.length)urgent.append(priorityRow(priorityOrder++,'Ready for your first genuine inquiry','Your intake is online. The recorded QA submission is not a real customer.','View cases','cases'));
 else urgent.append(priorityRow(priorityOrder++,'No urgent items in this snapshot','Check the case pipeline for new evidence and follow-up opportunities.','Cases','cases'));
 if(open.length&&!overdue.length)urgent.append(priorityRow(priorityOrder++,open.length+' open follow-up'+(open.length===1?'':'s'),'Track due dates and completion evidence.','Work queue','tasks'));
 if(current.drafts.length)urgent.append(priorityRow(priorityOrder++,current.drafts.length+' private content draft'+(current.drafts.length===1?'':'s'),'Reviewed drafts remain private until separately published.','Review','social'));
};
const originalDrawGrowth=drawGrowth;
drawGrowth=function(){
 originalDrawGrowth();
 const root=byId('channels');
 const items=[...root.querySelectorAll('.box')];
 const counts=items.map(x=>{const m=x.textContent.match(/(\d+) inbound inquiry/);return m?Number(m[1]):0});
 const max=Math.max(1,...counts);
 items.forEach((item,i)=>{
  const title=item.querySelector('strong');
  const summary=item.querySelector('p');
  if(!title||!summary)return;
  summary.textContent=counts[i]+' recorded inquiry'+(counts[i]===1?'':'ies')+' · source tag only';
  const meter=el('div',undefined,'source-meter');
  const bar=el('span');bar.style.width=(counts[i]/max*100).toFixed(1)+'%';meter.append(bar);
  item.append(meter);
 });
};
const originalRender=render;
render=function(){
 originalRender();
 byId('sync-time').textContent='Synced '+new Date(current.observedAt).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
 byId('sync-dot').classList.remove('error');
};
for(const button of byId('case-filters').querySelectorAll('button[data-filter]')){
 button.addEventListener('click',()=>{
  activeCaseFilter=button.dataset.filter;
  drawCases();
 });
}
for(const button of byId('task-filters').querySelectorAll('button[data-filter]')){
 button.addEventListener('click',()=>{
  activeTaskFilter=button.dataset.filter;
  drawTasks();
 });
}
for(const button of byId('mobile-dock').querySelectorAll('button[data-tab]')){
 button.addEventListener('click',()=>show(button.dataset.tab));
}
const moreToggle=byId('more-toggle');
moreToggle.addEventListener('click',()=>{
 const sheet=byId('more-sheet'),open=!sheet.classList.contains('open');
 sheet.classList.toggle('open',open);
 moreToggle.setAttribute('aria-expanded',open?'true':'false');
});
for(const button of byId('more-sheet').querySelectorAll('button[data-more-tab]')){
 button.addEventListener('click',()=>show(button.dataset.moreTab));
}
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'){
  byId('more-sheet').classList.remove('open');
  moreToggle.setAttribute('aria-expanded','false');
 }
 if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){
  event.preventDefault();show('cases');byId('search').focus();
 }
});
byId('see-cases').addEventListener('click',()=>show('cases'));
show('today');
`;
