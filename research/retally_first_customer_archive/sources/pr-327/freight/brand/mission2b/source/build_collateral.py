from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_ROW_HEIGHT_RULE
from pathlib import Path
import json,hashlib,datetime,os
OUT=Path(os.environ.get("RETALLY_OUTPUT_DIR", str(Path(__file__).resolve().parent.parent))).resolve(); DOCS=OUT/"docx"; SRC=OUT/"source"
DOCS.mkdir(parents=True, exist_ok=True)
TRUTH=json.loads((SRC/"commercial_truth.json").read_text())
for kind,filename in [("wordmark","retally-wordmark-approved.png"),("emblem","retally-emblem-approved.png")]:
    actual=hashlib.sha256((OUT/"assets"/filename).read_bytes()).hexdigest()
    assert actual == TRUTH["approved_brand"][f"{kind}_sha256"], f"Approved {kind} source hash mismatch"
LOGO=str(OUT/'assets/retally-wordmark-approved.png')
EMBLEM=str(OUT/'assets/retally-emblem-approved.png')
INK='0E1E29'; DEEP='06392F'; EMERALD='05B873'; GREEN='087A50'; MIST='EFF5F2'; GREY='576D71'; WHITE='FFFFFF'
DATE='08 OCT 2026'; ISSUE='M2C v1.0'; SITE=TRUTH['verified_documentary_facts']['website']; POSITIONING=TRUTH['approved_brand']['positioning']; TAGLINE=TRUTH['approved_brand']['tagline']

def shade(cell,fill):
 tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill);tcPr.append(shd)
def cell_border(cell,side='bottom',color='DDE8E3'):
 pr=cell._tc.get_or_add_tcPr(); bs=pr.first_child_found_in('w:tcBorders')
 if bs is None: bs=OxmlElement('w:tcBorders');pr.append(bs)
 el=OxmlElement(f'w:{side}');el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),color);bs.append(el)
def keep_with_next(p): p.paragraph_format.keep_with_next=True

def add_text(doc,text='',style=None,bold=False,color=None,size=None,space_after=5):
 p=doc.add_paragraph(style=style)
 r=p.add_run(str(text));r.bold=bold
 if color:r.font.color.rgb=RGBColor.from_string(color)
 if size:r.font.size=Pt(size)
 p.paragraph_format.space_after=Pt(space_after)
 return p

def line(doc,label,value):
 p=doc.add_paragraph();p.paragraph_format.space_after=Pt(5)
 r=p.add_run(label+'  ');r.bold=True;r.font.color.rgb=RGBColor.from_string(INK)
 p.add_run(value)
 return p

def heading(doc,text,level=1):
 p=doc.add_paragraph(text,style=f'Heading {level}');keep_with_next(p);return p

def note(doc,text,kind='NOTE'):
 t=doc.add_table(rows=1,cols=1);t.autofit=False;t.columns[0].width=Inches(7.13)
 c=t.cell(0,0);shade(c,MIST);p=c.paragraphs[0];p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3)
 r=p.add_run(kind+'  ');r.bold=True;r.font.color.rgb=RGBColor.from_string(GREEN);r.font.size=Pt(8.5)
 r=p.add_run(text);r.font.size=Pt(8.5)
 doc.add_paragraph().paragraph_format.space_after=Pt(0)

def table(doc,headers,rows,widths=None,small=False):
 t=doc.add_table(rows=1,cols=len(headers));t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER
 if widths:
  for i,w in enumerate(widths):t.columns[i].width=Inches(w)
 for i,h in enumerate(headers):
  c=t.rows[0].cells[i];shade(c,INK);r=c.paragraphs[0].add_run(str(h));r.bold=True;r.font.size=Pt(8.5 if small else 9);r.font.color.rgb=RGBColor(255,255,255)
 t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
 for j,row in enumerate(rows):
  cells=t.add_row().cells
  for k,v in enumerate(row):
   c=cells[k];c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   if j%2==0:shade(c,'F5F8F6')
   p=c.paragraphs[0];p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2)
   r=p.add_run(str(v));r.font.size=Pt(8.5 if small else 9);r.font.color.rgb=RGBColor.from_string(INK)
   if k==0:r.bold=True
   if k==len(row)-1 and (' $' in str(v) or str(v).startswith('$')):p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
   cell_border(c)
 doc.add_paragraph().paragraph_format.space_after=Pt(0)
 return t

def page(doc): doc.add_page_break()
def bullet(doc,text):
 p=doc.add_paragraph(style='List Bullet');p.paragraph_format.space_after=Pt(4);p.add_run(text)

def make(title,status='REVIEW DRAFT',code='M2C-00'):
 d=Document();sec=d.sections[0];sec.page_height=Inches(11);sec.page_width=Inches(8.5);sec.top_margin=Inches(.88);sec.bottom_margin=Inches(.72);sec.left_margin=Inches(.72);sec.right_margin=Inches(.72);sec.header_distance=Inches(.23);sec.footer_distance=Inches(.35)
 styles=d.styles;normal=styles['Normal'];normal.font.name='Carlito';normal.font.size=Pt(10.3);normal.font.color.rgb=RGBColor.from_string(INK);normal.paragraph_format.space_after=Pt(5)
 for lvl,size,col in [(1,15.0,INK),(2,11.5,GREEN),(3,10.0,DEEP)]:
  st=styles[f'Heading {lvl}'];st.font.name='Carlito';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor.from_string(col);st.paragraph_format.space_before=Pt(11 if lvl==1 else 8);st.paragraph_format.space_after=Pt(4)
 header=sec.header;hp=header.paragraphs[0];hp.alignment=WD_ALIGN_PARAGRAPH.LEFT;hp.paragraph_format.space_after=Pt(0)
 hp.add_run().add_picture(LOGO,width=Inches(1.82))
 p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT;p.paragraph_format.space_before=Pt(0)
 r=p.add_run(f'RETALLY  |  {code}  |  {ISSUE}  |  {status}     •     ');r.font.size=Pt(7);r.font.color.rgb=RGBColor.from_string(GREY)
 f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');p._p.append(f)
 d.add_paragraph('');p=d.add_paragraph(title,style='Title');p.alignment=WD_ALIGN_PARAGRAPH.LEFT;p.paragraph_format.space_after=Pt(6);p.runs[0].font.name='Carlito';p.runs[0].font.bold=True;p.runs[0].font.size=Pt(22);p.runs[0].font.color.rgb=RGBColor.from_string(INK)
 p=d.add_paragraph(f'{DATE}  |  {code}  |  {status}');p.paragraph_format.space_after=Pt(9);r=p.runs[0];r.font.size=Pt(8);r.font.color.rgb=RGBColor.from_string(GREY)
 return d

def save(d,name):
 path=DOCS/(name+'.docx');d.save(path);return path

# Canonical synthetic arithmetic and source provenance gate: no invented allocation.
from financial_controls import aggregate_arithmetic, worked_invoice
WORKED=worked_invoice(TRUTH['worked_invoice'])
AGGREGATE=aggregate_arithmetic(TRUTH['synthetic_public_aggregate'])
assert WORKED == {'expected':'1042.60','billed':'1167.60','variance':'125.00'}
assert AGGREGATE['unallocated_difference_usd']=='1650.00' and not AGGREGATE['fee_eligible_source_verified']
assert TRUTH['synthetic_public_aggregate']['usd']['gross_posted_recovery']=='14200.00'
assert TRUTH['synthetic_public_aggregate']['usd']['reversals']=='750.00'
assert TRUTH['synthetic_public_aggregate']['usd']['net_posted_recovery']=='13450.00'
assert TRUTH['synthetic_public_aggregate']['usd']['published_fee_eligible']=='11800.00'

# 01 SAMPLE REPORT
D=make('Sample Recovery Report',status='SAMPLE / NOT CLIENT PROOF',code='M2C-01')
add_text(D,TAGLINE,bold=True,color=GREEN,size=13)
note(D,'Illustrative information only. Northstar Industrial Supply, Blue River Freight, document IDs and all financial results are synthetic and are not RETALLY customer achievements.','SAMPLE ONLY')
heading(D,'Executive overview')
line(D,'Sample organization','Northstar Industrial Supply | multi-site distributor | illustrative 2026-01-01 to 2026-03-31')
line(D,'Illustrative population','1,284 records; 37 candidates; 14 validated findings; 9 authorized and submitted; 7 approved; 6 recovery events posted; 1 event reversed.')
line(D,'Audit boundary','Historical freight billing review. Actual carrier names, rate documents, source register and client-specific exclusions are not supplied for the published aggregate example.')
table(D,['Reporting state','Published synthetic aggregate','Not the same as'],[
 ['Candidate difference','$38,250.00','Validated loss or receivable'],['Validated difference','$24,100.00','Customer-authorized claim'],['Approved claim value','$17,650.00','Cash or posted credit'],['Gross posted recovery','$14,200.00','Net of reversals'],['Reversals','($750.00)','Additional cash recovery'],['Net actual recovery','$13,450.00','Fee-eligible amount'],['Fee-eligible value (published)','$11,800.00','Verified fee base without attribution register']],widths=[2.28,2.15,2.5])
heading(D,'Decision summary')
bullet(D,'The gross-to-net calculation reconciles arithmetically: $14,200 - $750 = $13,450.')
bullet(D,'The published $11,800 fee-eligible figure differs from net recovery by $1,650. Source-level exclusion and attribution records were not available. Treat fee eligibility as UNVERIFIED.')
bullet(D,'No contingency percentage, buyer net benefit or customer return on investment is established by this sample.')
page(D)
heading(D,'01  Reproducible invoice example')
add_text(D,'Independent micro-scenario, NOT included in the aggregate Northstar pipeline totals above.',bold=True,color=GREEN,size=9)
line(D,'Customer / carrier / shipment','Northstar Industrial Supply / Blue River Freight / FR-1001 (all illustrative).')
line(D,'Synthetic evidence IDs','INV-FR-1001 (invoice); RATE-FR-2026-A (rate confirmation); POD-FR-1001 (shipment/service confirmation); CR-FR-1001 (posted credit illustration).')
table(D,['Invoice line','Documented expected','Billed','Difference'],[
 ['Base freight','$820.00','$820.00','$0.00'],['Fuel 18% × $820','$147.60','$147.60','$0.00'],['Authorized liftgate','$75.00','$75.00','$0.00'],['Second unsupported liftgate','$0.00','$125.00','$125.00'],['TOTAL','$1,042.60','$1,167.60','$125.00']],widths=[2.74,1.5,1.34,1.38])
heading(D,'Rate-to-receipt evidence chain')
table(D,['Checkpoint','Illustrative source','Audit decision'],[
 ['Controlling authority','RATE-FR-2026-A','Base $820; fuel 18%; single $75 liftgate'],['Shipment record','POD-FR-1001','One confirmed liftgate; no evidence supporting a second'],['Carrier invoice','INV-FR-1001','Additional $125 accessorial line billed'],['Validation','CALC-FR-1001','Expected $1,042.60 versus billed $1,167.60'],['Customer decision','AUTH-FR-1001','Illustrative claim-specific written authorization'],['Posted settlement','CR-FR-1001','Illustrative $125 credit; settlement scenario only']],widths=[1.42,1.58,4.0],small=True)
heading(D,'Ledger test')
table(D,['Moment','Supported','Authorized','Actually received'],[
 ['Before evidence review','$0.00','$0.00','$0.00'],['Validated calculation','$125.00','$0.00','$0.00'],['After written authorization','$125.00','$125.00','$0.00'],['If/when credit posts','$125.00','$125.00','$125.00']],widths=[2.2,1.55,1.55,1.65],small=True)
note(D,'These are synthetic source IDs and simulated events, not links to actual documents. A live client finding must attach the controlling originals and actual dated approval/credit evidence.','EVIDENCE LIMIT')
page(D)
heading(D,'02  Population & pipeline')
add_text(D,'Counts below reproduce the publicly published sample. Conversion ratios describe this synthetic dataset only.')
table(D,['Stage','Count','Interpretation'],[
 ['Reviewed records','1,284','Defined sample audit population'],['Candidates flagged','37','Investigate; not validated'],['Findings validated','14','Source-supported within sample narrative'],['Claims authorized','9','Require discrete client authorization'],['Claims submitted','9','Submitted only after authorization'],['Claims approved','7','Carrier decision, not receipt'],['Recovery events posted','6','Illustrative financial posting'],['Recovery events reversed','1','Recovery reduction; not incremental value']],widths=[2.37,.65,3.95])
heading(D,'03  Detailed finding register, minimum production schema')
table(D,['Field','Required contents'],[
 ['Finding identity','Unique ID, exact invoice/line/shipment, carrier, mode, amount, issue category'],['Commercial authority','Contract/rate revision, effective window, tariff hierarchy and service conditions'],['Recalculation','Expected charge, invoiced charge, variance, rounding/currency convention'],['Evidence links','Source filenames or controlled record locators, reviewer, review timestamp'],['Approval','Customer decision, approving person, scope and decision timestamp'],['Recovery','Claim ID, carrier response, settlement/credit, reversal and accounting attribution']],widths=[1.48,5.48])
heading(D,'Evidence gaps in aggregate sample')
bullet(D,'No complete 1,284-record invoice population or original agreement versions attached to the publicly accessible sample summary.')
bullet(D,'No individual finding or settlement ledger capable of independently recomputing the $24,100 and $14,200 published aggregate amounts.')
bullet(D,'No signed fee terms or itemized $1,650 eligibility adjustment underlying the published $11,800 figure.')
page(D)
heading(D,'04  Settlement reconciliation and fee base')
table(D,['Reconciliation line','Amount','Evidence status'],[
 ['Gross posted recoveries','$14,200.00','Published synthetic value; itemization unavailable'],['Less: reversed postings','($750.00)','Published synthetic value; itemization unavailable'],['Net actual recovery','$13,450.00','Arithmetic VERIFIED; source attribution unverified'],['Difference to reported fee base','($1,650.00)','UNRESOLVED attribution / exclusion difference'],['Published fee-eligible amount','$11,800.00','Arithmetic difference only; eligibility NOT VERIFIED']],widths=[2.37,1.3,3.29])
note(D,'The $1,650 line is a reconciliation difference, NOT an asserted business exclusion. It may not be labeled incumbent-known, automatic credit, already-disputed, duplicate or contractual exclusion without the underlying eligible-item records.','HARD HOLD')
heading(D,'Fee and buyer-benefit semantics')
line(D,'Eligible fee base','Requires individual credits, contract exclusions, pre-existing claim status, attribution and written commercial terms.')
line(D,'Contingency fee','Cannot be calculated for this aggregate until a signed percentage and validated eligible base exist.')
line(D,'Customer net benefit','Net actual recovery minus agreed fees minus measured incremental customer operating cost; if cost is unknown, do not claim ROI.')
heading(D,'Illustrative fee formula (separate training scenario)')
table(D,['Training input','Value'],[['Eligible posted recovery (assumed)','$125.00'],['Assumed contingency rate, hypothetical only','20%'],['Illustrative fee: $125 × 20%','$25.00'],['Illustrative customer remainder before own costs','$100.00']],widths=[4.8,2.16])
note(D,'The 20% rate is a hypothetical arithmetic teaching device, not RETALLY pricing or a sales offer; no fee is due absent signed eligibility and commercial terms.','ILLUSTRATION')
page(D)
heading(D,'05  Controls, next actions & glossary')
heading(D,'What an actual customer would approve',2)
bullet(D,'Agree a bounded review population and controlling rate-authority hierarchy.')
bullet(D,'Provide records only through a separately verified, approved secure-transfer process.')
bullet(D,'Review and sign off each evidence-supported external recovery action before any carrier contact.')
bullet(D,'Review posted settlement amounts and excluded opportunities before any fee calculation.')
heading(D,'Control register')
table(D,['Control','Acceptance evidence'],[
 ['Population and duplicate prevention','Invoice IDs and already-known claim/credit exclusions cross-referenced'],['Rate authority','Effective contract edition, incorporated schedule, and service proof'],['Financial precision','Rounding, currency, offsets, reversals and actual posting references'],['Approval','Written claim-specific customer authorization'],['Privacy','Documented transfer, access, retention and deletion, not an ordinary inquiry email'],['Fee base','Signed fee terms and item-by-item eligible receipt ledger']],widths=[2.05,4.9])
heading(D,'State glossary')
for a,b in [('Candidate','Algorithmic or manual flag awaiting independent review.'),('Supported','Discrepancy whose relevant sources and computation have been reviewed.'),('Authorized','Claim-specific external action accepted in writing by the customer.'),('Approved','Carrier has accepted a claim; money may not yet be received.'),('Received','Cash or credit actually posted and uniquely allocated.'),('Reversed','Posted benefit canceled or offset after initial posting.'),('Fee-eligible','Portion of net attributable realized value meeting separately signed fee terms.')]:line(D,a,b)
note(D,'Do not use synthetic data as evidence of customer savings, recovered funds, capability validation, external assurance or commercial performance. This report is suitable only as an explicitly identified example.','RELEASE CONDITION')
save(D,'01_Sample_Recovery_Report')

# 02 BUYER ONE PAGER
D=make('A clear audit. Not a guess.',status='CONTACT / LEGAL GATES',code='M2C-02')
add_text(D,'Independent freight invoice review and recovery support',color=GREEN,bold=True,size=12)
add_text(D,POSITIONING,bold=True,size=10.5)
heading(D,'Where RETALLY looks')
add_text(D,'Agreed historical freight invoices can contain duplicate charges, rate variances, unsupported accessorials or missed credits. Every identified issue remains a candidate until checked against relevant shipment and commercial records.')
heading(D,'Three accountable stages')
table(D,['FIND IT','PROVE IT','RECOVER IT'],[['Bounded invoices, shipment references, rate terms and credits.','Calculation and source records, with unsupported items clearly excluded.','Only with separate customer approval; distinguish claim status from posted funds.']],widths=[2.29,2.29,2.29])
heading(D,'What the customer receives')
bullet(D,'Defined invoice population, scope, exclusions and evidence gaps.')
bullet(D,'Finding register with source authority, amount, reviewer decision and next action.')
bullet(D,'Recovery ledger separating approved claims from actual credits, refunds and reversals.')
heading(D,'Commercial arrangement')
line(D,'Initial review','$0 upfront for mutually agreed, eligible and bounded scope.')
line(D,'Recovery support','Optional; separate written authorization and signed terms. Fees only on defined eligible actual recoveries; no guarantees.')
heading(D,'First step')
add_text(D,'Discuss the review fit and required records. Do not attach confidential invoices, rates or bank information to an initial inquiry.')
note(D,'Contact route: retallyrecovery.com (use only after domain and inbound inquiry verification). No binding offer or approved contingency rate is made by this document.','DISTRIBUTION HOLD')
save(D,'02_Buyer_One_Pager')

# 03 PROPOSAL
D=make('Freight Audit & Recovery Proposal',status='CUSTOMIZABLE / NONBINDING',code='M2C-03')
add_text(D,'Evidence first. External action only after customer authorization.',bold=True,color=GREEN,size=11)
note(D,'Engagement-specific customer names, rates, prices and dates must be inserted through an approved scope worksheet before transmission. This is a proposal framework, not an executed contract.','TEMPLATE')
heading(D,'Executive proposition')
add_text(D,'RETALLY proposes an independent review of a mutually defined historical freight invoice population. The purpose is to identify supportable billing discrepancies, make the evidence and calculations reviewable and, if independently authorized, assist recovery of eligible overpayments.')
heading(D,'Proposed scope boundaries')
table(D,['Field to agree','Decision recorded before work'],[
 ['Customer and legal counterpart','Confirm actual contracting entities and authorized representatives.'],['Review population','Named carriers, shipment modes, invoice IDs, paid status and review period.'],['Source authority','Rate confirmations, amendments, tariffs and relevant service proofs.'],['Known activity','Credits, disputed amounts, incumbent reviews, open claims, recoveries.'],['Exclusions','Explicit carrier/date/charge, service and jurisdiction exclusions.'],['Acceptance / timing','Agree data completeness criteria and milestone dates.']],widths=[2.0,4.93])
heading(D,'Deliverable package')
bullet(D,'Executive audit summary and population coverage statement.')
bullet(D,'Evidence register with source record references and item-level computations.')
bullet(D,'Prioritized supported findings and gaps, with no unsupported savings estimates.')
bullet(D,'Authorization-ready recovery list and actual-receipts reconciliation if later engaged.')
page(D)
heading(D,'Review methodology')
table(D,['Step','RETALLY work','Customer decision / dependency'],[
 ['01  Agree','Define the bounded universe and authoritative sources.','Approve scope, exclusions and representative.'],['02  Transfer','Confirm separate approved secure intake and record inventory.','Supply requested records through approved route.'],['03  Reconcile','Compare billed lines against contract, shipment and credits.','Respond to ambiguous contract or service facts.'],['04  Validate','Human-review calculations, source hierarchy and duplicates.','Accept evidence findings and request clarification.'],['05  Authorize','Prepare claim-specific options, if eligible.','Provide explicit written external-action approvals.'],['06  Account','Reconcile settlements, credits, reversals and eligibility.','Confirm accounting attribution and fee terms.']],widths=[1.11,2.7,3.1],small=True)
heading(D,'Financial reporting rules')
for a,b in [('Candidate','Unvalidated difference; not a receivable, claim or savings.'),('Supported finding','Reviewed evidence and calculation; not an authorization.'),('Customer-authorized','Specific claim/action approved in writing; no received funds implied.'),('Posted recovery','Uniquely attributed cash or credit actually recorded, reduced for reversals.'),('Fee-eligible','Only actual recovery meeting exclusions and definitions of a separately signed agreement.')]:line(D,a,b)
heading(D,'Example deliverable acceptance checklist')
bullet(D,'The customer can re-perform every included supported-finding calculation.')
bullet(D,'The report identifies all material source gaps and excluded/pre-existing claims.')
bullet(D,'Every settlement or credit is linked to a source entry and not counted twice.')
heading(D,'Customer resource commitments')
add_text(D,'The review depends on designated contacts for transportation, AP/accounting and contract interpretation. Actual data access, expected turnaround and any customer IT effort must be determined after scoping; none is guaranteed here.')
page(D)
heading(D,'Commercial and confidentiality boundaries')
table(D,['Subject','Proposed treatment / unresolved approval'],[
 ['Initial review','$0 upfront only for an agreed eligible scope; define work limit in writing.'],['Recovery fee','Percentage and fee-eligible base MUST be in separately signed terms.'],['Outreach / disputes','None without claim-specific customer authorization.'],['Confidential transfer','Confirm secure, access-limited transfer before supplying invoices or rates.'],['Retention and deletion','Requires an approved policy and applicable agreement; not asserted here.'],['Legal entity and venue','Verify legal contracting party and obtain appropriate legal review.'],['No guarantee','No promised recovery amount, rate or processing timeline.']],widths=[1.72,5.2])
heading(D,'Proposed milestones (dates intentionally not promised)')
for a,b in [('A / Scope approved','Record commercial boundary, reviewers and secure transfer.'),('B / Intake accepted','Reconcile completeness and confirm evidence references.'),('C / Findings reviewed','Deliver findings, decisions, calculations and exclusions.'),('D / Optional recovery','Separate engagement; customer-directed external claim decisions.'),('E / Settlement accounting','Verify posted receipts, reversals and contractual eligibility.')]:line(D,a,b)
heading(D,'Next decision')
add_text(D,'Agree whether a bounded initial review is appropriate and verify the identity, engagement, security and commercial gates before exchanging confidential records.')
note(D,'This is a nonbinding presentation template; not a service agreement, NDA, data-processing agreement or carrier-claim authorization. Final terms require legal review.','APPROVAL REQUIRED')
save(D,'03_Commercial_Proposal')

# 04 PRICING
D=make('Pricing & Scope, Explained',status='TERMS NOT EXECUTED',code='M2C-04')
heading(D,'Two separate decisions')
table(D,['Initial review','Optional recovery engagement'],[['$0 upfront for an explicitly agreed eligible scope. No promise of unlimited data analysis or time.','Claim-specific customer approval, separately signed contingency terms and defined eligible actual receipts.']],widths=[3.47,3.47])
heading(D,'Scope should define')
for txt in ['Which carriers, modes, periods and paid invoice populations are eligible.','What source records are required, who supplies them and when a sample is deemed complete.','Whether pre-existing disputes, automatic credits, known rate corrections or other matters are excluded.','Who may approve findings, outside recovery actions and final financial reconciliations.']:bullet(D,txt)
heading(D,'What the fee is NOT based on')
bullet(D,'An unreviewed variance, algorithmic flag, estimated leakage or unsupported credit.')
bullet(D,'A submitted or even approved claim before funds or credits actually post.')
bullet(D,'Amounts excluded by the signed agreement or double-counted elsewhere.')
heading(D,'Arithmetic training example | NOT RETALLY PRICING')
table(D,['Illustrative step','Amount'],[['Actual posted eligible receipt','$1,000.00'],['Hypothetical contingency rate','20%'],['Illustrative service fee','$200.00'],['Customer remainder before measured internal costs','$800.00']],widths=[5.12,1.84])
note(D,'The 20% assumption is not a quote, approved rate or representation of current offers. The actual fee, fee base, timing, tax treatment, reversals and invoice terms must be separately agreed.','HYPOTHETICAL')
page(D)
heading(D,'What changes the fee base?')
table(D,['Situation','Treatment to settle contractually'],[
 ['Existing carrier credit','Confirm if already known or automatic; do not double-charge.'],['Prior customer claim','Confirm attribution and any exclusion.'],['Credit later reversed','Apply reversal and fee-adjustment rules in signed terms.'],['Partial carrier recovery','Recognize only attributable posted amount.'],['Currency or tax adjustments','Agree treatment in signed terms; avoid unsupported equivalence.'],['Refund from multiple audits','Allocate uniquely, preserve source trace.']],widths=[2.22,4.71])
heading(D,'Fee verification protocol')
for s in ['Read the signed fee definition and eligible categories.','Trace each eligible receipt to claim, invoice and original customer authorization.','Subtract reversals, excluded and duplicate-attributed receipts.','Compute fees on the contractually permitted base, not on an aspirational savings estimate.',"Identify the customer's measured incremental costs before asserting net ROI."]:bullet(D,s)
heading(D,'Questions RETALLY must answer before signing')
add_text(D,'What is the exact percentage? What is the attribution window? Who handles disputes, refunds and credit memos? When is a fee earned and invoiced? What happens after reversals? What customer work or service limits apply? What legal name is on the contract?')
note(D,'This explanatory document is not a contract. No rate or fee entitlement is created.','NONBINDING')
save(D,'04_Pricing_and_Scope')

# 05 WELCOME
D=make('Customer Welcome & Data Readiness',status='ONBOARDING CONTROLLED DRAFT',code='M2C-05')
heading(D,'Before any confidential document is transferred')
add_text(D,'The objective is a review that is bounded, properly authorized and reproducible. A public inquiry or an introductory email is not a secure delivery channel for freight billing records.')
table(D,['Gate','Owner / acceptance condition'],[
 ['1. Confirm business identity','RETALLY and customer verify legal names and authorized representatives.'],['2. Define boundaries','Approve dates, carriers, modes, expected volume and exclusions.'],['3. Approve confidentiality terms','Legal/authorized owners confirm confidentiality and permitted use.'],['4. Verify intake channel','Security/data owner documents approved transfer path and access rights.'],['5. Inventory sources','Identify invoices, shipment references, rate authority, paid/credit records.'],['6. Validate completeness','Reconcile record counts, missing files and data-quality exceptions.'],['7. Start review','Begin only within approved scope; log changes and decisions.']],widths=[2.35,4.58],small=True)
heading(D,"Customer's key records")
bullet(D,'Freight invoices and line-level charges for agreed review population.')
bullet(D,'Shipment IDs, manifests, proofs of delivery/service and accessorial authorizations.')
bullet(D,'Signed contracts, applicable rate schedules, amendments and effective dates.')
bullet(D,'Payment ledgers, credit memos, past disputes and pre-existing claims.')
heading(D,'Customer control')
note(D,'Silence is not approval. A report or candidate finding cannot by itself authorize outside carrier communications. Written, claim-specific approval is a separate event.','AUTHORIZATION')
page(D)
heading(D,'Onboarding readiness worksheet')
table(D,['Review item','Evidence or decision needed'],[
 ['Designated customer lead','Verified name, title, role and approved decision authority'],['Participating internal functions','AP/controller, transportation and contract/rates contacts'],['Scope reference','Approved population ID, date range, exceptions and known disputes'],['Data-transfer channel','Approved secure method and owner, not a generic email'],['Access control','Named readers, permissions and retention/deletion requirements'],['Data inventory','Exact count of invoices, shipment proofs, rate files and payment/credit records'],['Completeness outcome','Missing records list, accepted gaps and approved start date']],widths=[2.3,4.63])
heading(D,'After findings are returned')
for a,b in [('Review meeting','Resolve disputed interpretations and discuss supported vs candidate findings.'),('Decisions','Approve or reject every proposed outside recovery claim individually.'),('Progress','Track carrier outcomes, posted credits, partial receipts and reversals.'),('Commercial billing','Apply only signed and confirmed fee terms to verified eligible amounts.')]:line(D,a,b)
note(D,'No actual storage provider, encryption configuration, access-control deployment or deletion timing is attested by this template. These must be validated before intake.','SECURITY GATE')
save(D,'05_Customer_Welcome_and_Onboarding')

# 06 STATUS
D=make('Recovery Status & Reconciliation',status='BLANK CONTROLLED TEMPLATE',code='M2C-06')
heading(D,'Report metadata')
add_text(D,'Customer / review ID: TO BE COMPLETED FROM APPROVED ENGAGEMENT | Reporting period: NOT SET | Reviewer: NOT ASSIGNED')
heading(D,'Executive financial bridge')
table(D,['Stage','Opening','Movement','Closing / proof'],[
 ['Candidates','No data','No data','Register required'],['Supported findings','No data','No data','Source & calculation links'],['Authorized claims','No data','No data','Signed decision records'],['Approved carrier claims','No data','No data','Carrier decision source'],['Gross posted recoveries','No data','No data','Settlement reference'],['Reversals','No data','No data','Reversal reference'],['Net actual recovery','No data','No data','Gross less reversals'],['Fee-eligible actual recovery','No data','No data','Verified contractual exclusions']],widths=[2.22,1.28,1.28,2.15],small=True)
heading(D,'Required identity fields for each recovery')
table(D,['Entity','Minimum trace'],[
 ['Finding','Unique ID, source invoice/line, amount and review status'],['Authorized action','Customer approving party, timestamp, action scope'],['Claim','Carrier claim reference, response and decision'],['Settlement','Credit memo, payment/statement posting and accounting allocation'],['Adjustment','Reversal, duplication exclusion, partial posting or offset'],['Fee determination','Actual eligible receipt and signed fee definition']],widths=[1.6,5.34])
heading(D,'Reconciliation checks')
bullet(D,'Closing state = opening state + additions - removals; status movement never silently creates cash.')
bullet(D,'Net actual recovery = uniquely attributed posted receipts - reversals.')
bullet(D,'Fee eligibility requires written contract definitions and evidence-backed exclusions.')
page(D)
heading(D,'Customer decision and exception log')
table(D,['Finding or question','State / assigned owner','Required decision'],[
 ['No live engagement supplied','NOT POPULATED','Enter actual references only after authorization'],['Ambiguous contractual rate term','IF PRESENT','Confirm controlling version / effective dates'],['Credit already received','IF PRESENT','Exclude double counting and verify attribution'],['Carrier claim / dispute','PENDING UNTIL AUTHORIZED','Separate written customer approval']],widths=[2.3,2.03,2.6])
heading(D,'Sign-off / publication controls')
for txt in ['Review recipient and date are actual and verified.','No sample/example numbers carried into real customer reporting.','All reported financial totals reconcile to attached registers.','Fee base and claim authority have independent, recorded approval.']:bullet(D,txt)
note(D,'This is a reporting structure, not a completed customer report. The absence of populated data must not be interpreted as zero findings or zero recovery.','TEMPLATE ONLY')
save(D,'06_Recovery_Status_Update')

# 07 ENGAGEMENT
D=make('Engagement Cover Sheet',status='NONBINDING / LEGAL REVIEW',code='M2C-07')
add_text(D,'This cover sheet records proposed review metadata. It is not a contract, claims authorization or confidentiality agreement.',bold=True,color=GREEN,size=10)
heading(D,'Proposed review terms for later completion')
table(D,['Control field','Required verified entry'],[
 ['Legal contracting party','Confirm registered entity and authorized trade name; NOT VERIFIED HERE'],['Customer and decision maker','Confirm authority, company and contact through customer source'],['Covered records','Specify carriers, invoice population, modes, dates and payment status'],['Exclusions','Specify prior claims, automatic credits, known adjustments, unsupported categories'],['Initial review','$0 upfront only for expressly agreed eligible bounded scope'],['Confidential intake','Separately verified secure method and approved confidentiality terms'],['Outside action','Requires separate documented claim-specific written customer authorization'],['Recovery terms','Separately signed contingency percentage, exclusions and timing'],['Eligibility rule','Net actual attributable receipts defined by signed terms']],widths=[2.15,4.79],small=True)
heading(D,'Approval boundary')
note(D,'Acknowledging receipt of this sheet does not bind either party to service, fee, confidentiality, exclusivity, third-party outreach or contract terms. Obtain appropriate legal review and signatures on separate legal documents.','NONBINDING')
heading(D,'Document controls')
add_text(D,'Version M2B v1.0 | Prepared 08 October 2026 | Contracting entity verification: OPEN | External action authority: NOT GRANTED')
save(D,'07_Engagement_Cover_Sheet')

# 08 EMAIL
D=make('Customer Email Templates',status='DO NOT AUTO-SEND',code='M2C-08')
note(D,'Templates are not sent, and should not contain confidential billing records or unsupported service assurances. Verify actual sender identity and inbound reception before use.','REVIEW BEFORE USE')
heading(D,'01  Inquiry acknowledgement')
line(D,'Subject','RETALLY | Your freight review inquiry')
add_text(D,'Thank you for contacting RETALLY. We can discuss whether a bounded review of your freight invoices is appropriate. We will first confirm scope and the information needed. Please do not send invoices, contracts, payment records or other confidential documents in an initial email. A secure transfer method must be confirmed separately before any records are supplied.')
add_text(D,'Signature: Verified sender details required before transmission.',color=GREY,size=8)
heading(D,'02  Scope confirmation')
line(D,'Subject','RETALLY | Proposed review boundaries')
add_text(D,'Following our discussion, please review the proposed carriers, periods, invoice population, exclusions and existing claims in the accompanying scope record. Confirm the business decision maker and the applicable source-rate records. This communication does not create fees, approve carrier outreach or replace signed commercial terms.')
add_text(D,'Signature: Verified sender details required before transmission.',color=GREY,size=8)
heading(D,'03  Secure evidence request')
line(D,'Subject','RETALLY | Review record checklist')
add_text(D,'Please use only the transfer method separately approved for this engagement to provide the agreed invoice, shipment, rate and payment/credit records. Do not reply with confidential attachments through this introductory thread. Include previously disputed items and existing credits to prevent duplicate recovery claims.')
add_text(D,'Signature: Verified sender details required before transmission.',color=GREY,size=8)
page(D)
heading(D,'04  Findings review and authorization')
line(D,'Subject','RETALLY | Findings ready for customer review')
add_text(D,'The review of the agreed population is ready for customer evaluation. The accompanying register distinguishes candidate discrepancies, supported findings, missing evidence and proposed actions. Please review each item. No carrier-facing action will be taken solely because this report was delivered; separate written authorization is required for each approved recovery action.')
heading(D,'05  Recovery-status update')
line(D,'Subject','RETALLY | Recovery status for approved engagement')
add_text(D,'The attached engagement-specific statement separates potential issues from validated findings, customer-authorized actions and net funds or credits actually received. Please consult the referenced settlement and reversal records for posted amounts. Decisions requiring customer action and unresolved documentation gaps are identified in the report. Any contingent fee is determined only under signed terms and verified eligible receipts.')
heading(D,'06  Review conclusion')
line(D,'Subject','RETALLY | Review completion and next steps')
add_text(D,'RETALLY has completed the agreed review stage and prepared a final summary of scope, reviewed evidence, supported findings, exclusions and remaining questions. The customer may decide whether to authorize any separate recovery activity. A lack of eligible discrepancies is a legitimate review result, not a promise of savings.')
note(D,'Each template is one standalone communication when extracted from the handbook. Legal, identity, security and actual engagement facts require final human confirmation.','APPROVAL')
save(D,'08_Customer_Email_Templates')

# 09 REFERRAL
D=make('Adviser & Referral Partner Brief',status='REVIEW / NO REFERRAL FEES APPROVED',code='M2C-09')
heading(D,'The opportunity')
add_text(D,'Accountants, fractional CFOs, AP consultants and logistics advisers may encounter freight expenses that warrant independent review. RETALLY offers bounded, evidence-based scrutiny rather than unsupported recovery promises.')
heading(D,'Where a referral may fit')
bullet(D,'Complex or multi-carrier historical invoice populations.')
bullet(D,'Suspected duplicate charges, rate variance, unsupported accessorials or missed credits.')
bullet(D,'A customer willing to share controlling contracts and financial records through a verified secure process.')
heading(D,'How introductions work')
table(D,['Step','Required boundary'],[
 ['Obtain permission','Customer authorizes introduction; share no confidential billing records.'],['Discuss suitability','Scope, carrier types, periods and available evidence are assessed.'],['Agree any review','Bounded eligible initial review at $0 upfront subject to agreed scope.'],['Protect authority','Separate written customer approval for carrier action and commercial terms.']],widths=[2.15,4.79])
heading(D,'Independence and compensation')
add_text(D,'No referral compensation is promised or implied by this brief. Any potential arrangements would require specific written disclosures, commercial approval and appropriate professional or legal review.')
note(D,'Prospective partner contact details and any applicable professional independence restrictions must be confirmed before use.','PARTNER GATE')
save(D,'09_Referral_Partner_Brief')

# 10 LETTERHEAD
D=make('RETALLY Correspondence',status='BLANK LETTERHEAD / HOLD',code='M2C-10')
line(D,'Reference','TO BE SET FROM ACTUAL MATTER')
line(D,'Subject','TO BE COMPLETED AFTER RECIPIENT VERIFICATION')
line(D,'Recipient','Actual recipient and organization required')
heading(D,'Correspondence body')
add_text(D,'Start with the decision, finding or requested action. Identify the controlling evidence and any deadlines that are actually agreed. Do not insert fabricated customer achievements or unsupported security statements.')
heading(D,'Evidence / enclosure reference')
add_text(D,'Link or identify only authorized records under an approved confidential-transfer procedure.')
heading(D,'Sender')
add_text(D,'Verified name, title, legal entity and direct contact are mandatory before release.')
note(D,'This is a blank template; it must never be forwarded to a prospective customer with these instructions intact.','NOT SENDABLE')
save(D,'10_Letterhead_Template')

# 11 CASE STUDY
D=make('Verified Case Study Template',status='PUBLICATION HOLD',code='M2C-11')
note(D,'No customer case study is published until verified real-world evidence and written customer permission are recorded. Never replace missing proof with synthetic metrics.','PUBLISHING BLOCKED')
heading(D,'Required release file')
table(D,['Requirement','Real evidence to record'],[
 ['Customer consent','Signed approval for identification or approved anonymous description'],['Review boundary','Specific covered carriers, invoice population, period and exclusions'],['Finding evidence','Source invoices, rate authority, recalculations and reviewer sign-off'],['Outcome confirmation','Carrier posted credits/cash, dated confirmations and reversals'],['Permission for claims','Written approval of every quote, graphic and aggregate number'],['Legal/privacy approval','Confidentiality and publicity restrictions cleared']],widths=[2.25,4.7])
heading(D,'Narrative structure')
for title,txt in [('01  The billing issue','Describe an evidenced problem and why the invoice or contract mattered.'),('02  Method','List source records, calculation standard, exclusions and reviewer controls.'),('03  Findings','Separate flags, supported differences and customer-authorized claims.'),('04  Realized results','Only report posted funds and credits with net reversal reconciliation.'),('05  Lessons','Explain material limits and practical buyer implications without guarantees.')]:
 heading(D,title,2);add_text(D,txt)
heading(D,'Permitted interim alternative')
add_text(D,'Use the explicitly labeled sample invoice-to-credit walkthrough as a process demonstration. Do not describe it as a published customer case study.')
save(D,'11_Verified_Case_Study_Template')

# 12 STYLE
D=make('Customer Document Design Standards',status='INTERNAL PRODUCTION STANDARD',code='M2C-12')
heading(D,'Identity and color')
add_text(D,'The original approved glossy charcoal RETALLY wordmark with green arrow A is the primary corporate mark. Use the approved separate R emblem only for suitable compact or selected cover roles; never pair it redundantly with the wordmark. Original artwork must remain unchanged.')
table(D,['Token','HEX','Use'],[['Ink','#0E1E29','Core titles, text and tables'],['Forest','#06392F','Selected dark identity surfaces'],['Emerald','#05B873','Brand accent, not automatically white-text contrast'],['Mist','#EFF5F2','Support panels and alternating table rows'],['Ledger gray','#576D71','Secondary information'],['Action green','#087A50','Verified contrast UI/actions']],widths=[1.6,1.45,3.88])
heading(D,'Print and layout')
for s in ['US Letter 8.5 × 11 inches, 0.72-inch horizontal margins and documented header/footer safe zones.','Use Aptos or equivalent office-safe sans for customer-document body; retain Hanken Grotesk and Instrument Serif on the website where approved.','Financial tables use 8 to 9-point dense cells where necessary, 9.5 to 11-point body text and clearly ranked headings.','Render embedded logo at native ratio from approved PNG masters; never alter the original pixel artwork.','Use right-aligned tabular monetary values, explicit units, periods, statuses and sources.','Maintain readable grayscale contrast and full sample disclosures on every illustrative financial document.','Provide report date, reference, version, owner and draft/approval state in metadata.']:bullet(D,s)
page(D)
heading(D,'Financial control language')
table(D,['State','Definition in customer copy'],[
 ['Candidate','Possible difference not validated'],['Supported','Source-backed calculation reviewed'],['Authorized','Separate customer action approved in writing'],['Approved','Carrier claims decision not money'],['Received','Actual uniquely allocated posted cash/credit, net of reversals'],['Fee-eligible','Only attributable realized benefit meeting signed terms']],widths=[1.8,5.14])
heading(D,'Acceptance before distribution')
for s in ['Compare editable source and exported PDF: every number, disclaimer, page and table must agree.','Review every rendered page for clipping, unexpected page breaks, broken logos, footers and unbalanced whitespace.','Search for drafting placeholders, unsupported customer claims, fictional proof and inaccurate contact routes.','Run independent financial recomputation and verify totals to source records or mark UNVERIFIED.','Require legal/entity review of binding documentation and independent confirmation of secure intake.','Maintain a signed publication manifest; release each artifact individually rather than treating the whole package as approved.']:bullet(D,s)
heading(D,'Source artwork integrity')
line(D,'Wordmark SHA-256','08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd')
line(D,'Emblem SHA-256','bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043')
note(D,'Source hashing establishes asset identity only, not final production approval, legal rights clearance, printer fidelity or customer release permission.','CONTROL')
save(D,'12_Customer_Document_Standards')

manifest=[]
for f in sorted(DOCS.glob('*.docx')):manifest.append({'source':f.name,'status':'INTERNAL/REVIEW' if any(q in f.name for q in ['03_','04_','05_','06_','07_','08_','09_','10_','11_']) else 'SAMPLE/REVIEW','size_bytes':f.stat().st_size})
(SRC/'manifest.json').write_text(json.dumps({'created':'2026-10-08','version':ISSUE,'documents':manifest},indent=2))
print('CREATED',len(manifest),'DOCX files')