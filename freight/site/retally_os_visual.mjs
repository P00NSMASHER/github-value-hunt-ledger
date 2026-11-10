/* Visual-only design tokens for the existing owner-only Pages UI. */
export const visualStyle = String.raw`/* RETALLY OS | V3 private command center. No external fonts, images or network dependencies. */
:root{color-scheme:dark;--bg:#060d18;--surface:#111e31;--surface2:#142438;--raised:#192d44;--edge:#263a50;--text:#f0f6ff;--muted:#91a5bc;--teal:#62ead1;--teal-dark:#0c625d;--purple:#b7a8ff;--gold:#f5c679;--red:#ff9b9e;--radius:20px;--shadow:0 22px 52px rgba(0,0,0,.24);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
*{box-sizing:border-box}
html{min-height:100%;background:var(--bg);scroll-behavior:smooth}
body{min-height:100vh;margin:0;overflow-x:hidden;color:var(--text);background:radial-gradient(80rem 37rem at 89% -18%,#21405c66,transparent 65%),radial-gradient(53rem 35rem at 2% 45%,#193b4266,transparent 70%),var(--bg);font-size:14px;-webkit-font-smoothing:antialiased}
body:before{content:"";position:fixed;z-index:0;inset:0;pointer-events:none;background-image:linear-gradient(#ffffff04 1px,transparent 1px),linear-gradient(90deg,#ffffff04 1px,transparent 1px);background-size:40px 40px;mask-image:linear-gradient(to bottom,#0005,transparent 72%)}
button,input,select,textarea{font:inherit}
button{cursor:pointer;color:var(--text);border:1px solid #32485f;background:#1c3047;border-radius:12px;min-height:42px;padding:10px 16px;font-weight:650;transition:background .16s,border-color .16s,transform .16s}
button:hover{background:#27415a;border-color:#5fbcb1}
button:active{transform:translateY(1px)}
button:disabled{opacity:.5;cursor:not-allowed;transform:none}
button.primary{background:linear-gradient(130deg,#84f5df,#56d5c8);color:#062e36;border:1px solid #99ffe1;box-shadow:0 8px 24px #34d5b130;font-weight:800}
button.primary:hover{background:#a6ffea}
a{color:var(--teal);text-underline-offset:3px}
a:hover{color:#b0fff1}
:focus-visible{outline:3px solid #84f0de;outline-offset:3px}
header{position:sticky;top:0;z-index:40;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px clamp(16px,3vw,38px);min-height:76px;border-bottom:1px solid #29435892;background:#080f1ce8;backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px)}
.brand{display:flex;align-items:center;gap:12px;flex-direction:row;font-size:21px;font-weight:850;letter-spacing:.13em;line-height:1.1}
.brand small{display:block;font-size:9px;letter-spacing:.24em;color:var(--teal);margin-top:5px}
.brand-copy{display:flex;flex-direction:column}
.brand-emblem{width:39px;height:39px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(145deg,#86ffe2,#41a6ab);color:#052f3a;font-size:23px;font-weight:1000;box-shadow:0 0 22px #50e0c852}
.right{display:flex;align-items:center;gap:12px}
.secure-label{display:flex;gap:7px;align-items:center;color:#b2c7d9;font-size:11px;letter-spacing:.07em;font-weight:720}
.secure-label:before{content:"";width:7px;height:7px;background:#4ee3b4;border-radius:50%;box-shadow:0 0 0 4px #4ee3b418}
.header-link{font-size:12px;color:#adbed0;text-decoration:none;padding:8px 4px}
#refresh{background:#1d354b;border-color:#36516b;min-height:38px;border-radius:11px;padding:9px 14px}
main{position:relative;z-index:1;max-width:1512px;margin:0 auto 0 240px;padding:32px clamp(20px,3.8vw,58px) 85px}
nav[aria-label="Workspace tabs"]{position:fixed;z-index:35;top:76px;left:0;bottom:0;width:240px;padding:23px 13px;background:#0b1727e8;border-right:1px solid #223649;display:flex;flex-direction:column;gap:5px;overflow-y:auto;margin:0}
.sidebar-section{font-size:10px;letter-spacing:.2em;color:#728da8;text-transform:uppercase;font-weight:900;padding:11px 15px 13px}
nav[aria-label="Workspace tabs"] button{display:flex;align-items:center;gap:12px;width:100%;border:1px solid transparent;background:transparent;border-radius:12px;color:#a4b9cf;text-align:left;justify-content:flex-start;font-weight:650;font-size:13px;padding:13px 14px;min-height:46px}
nav[aria-label="Workspace tabs"] button:hover{background:#1b3044}
nav[aria-label="Workspace tabs"] button.active{background:linear-gradient(92deg,#173d43,#16313b);color:#a6fff0;border-color:#2b736b;box-shadow:inset 3px 0 0 #4fe1c4}
.nav-icon{width:22px;font-size:12px;letter-spacing:0;color:#6fd5c4;font-weight:850}
.sidebar-footer{font-size:11px;line-height:1.7;color:#7f9ab1;margin:auto 13px 12px;border-top:1px solid #294257;padding-top:18px}
.page-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin:0 0 23px}
.eyebrow{font-size:10px;letter-spacing:.23em;font-weight:850;color:#91e1d3;text-transform:uppercase}
h1{font-size:clamp(29px,3.6vw,43px);letter-spacing:-.05em;line-height:1.1;margin:10px 0}
h2{font-size:clamp(19px,2vw,24px);letter-spacing:-.025em;margin:0 0 15px}
h3{font-size:16px;letter-spacing:-.02em;margin:0}
p{line-height:1.55}
.lead{margin:0;color:#a9bbcf;max-width:600px;font-size:14px;line-height:1.6}
.sync-indicator{display:flex;align-items:center;gap:9px;color:#9db5c7;border:1px solid #2d4658;background:#112335;padding:10px 13px;border-radius:100px;white-space:nowrap;font-size:11px}
.sync-dot{width:8px;height:8px;border-radius:50%;background:#55dfb5;box-shadow:0 0 12px #55dfb599;flex:none}
.panel{display:none}
.panel.active{display:block;animation:fadeIn .22s ease both}
@keyframes fadeIn{from{opacity:.45;transform:translateY(5px)}to{opacity:1;transform:none}}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:16px 0 25px}
#metrics.grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.tile,.box,.case,.draft{border:1px solid #2b4056;background:linear-gradient(143deg,#13253a,#101e30);border-radius:var(--radius);box-shadow:var(--shadow)}
.box,.case,.draft{padding:22px}
.tile{min-height:145px;padding:20px;text-align:left;display:flex;flex-direction:column;align-items:flex-start;justify-content:space-between;background:linear-gradient(140deg,#182e43,#102034);position:relative;overflow:hidden}
.tile::after{content:"";position:absolute;width:120px;height:120px;right:-53px;top:-72px;border-radius:50%;background:#77ebd00d;border:1px solid #7fead21b}
.tile:hover{border-color:#3f8b80;background:linear-gradient(145deg,#1c384e,#14263b)}
.tile strong{font-size:clamp(32px,3.4vw,44px);line-height:1;letter-spacing:-.06em;color:#fff;margin:12px 0 0;font-weight:800;font-variant-numeric:tabular-nums}
.tile .label{display:block;font-weight:650;color:#a1b9ce;font-size:12px}
.tile .kpi-detail{color:#718fa7;font-size:11px;margin-top:14px}
.tile.attention{border-color:#70533e;background:linear-gradient(145deg,#292b34,#1d2633)}
.tile.attention strong{color:var(--gold)}
.two{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:17px}
.stack{display:grid;gap:14px}
.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:22px 0 14px}
.section-head h2{margin:0}
.section-overline{color:#7e9cb5;letter-spacing:.17em;text-transform:uppercase;font-size:10px;font-weight:850}
.case,.draft{position:relative;min-width:0}
.case h3,.draft h3{font-size:17px;line-height:1.3;margin:0 0 5px;font-weight:760;overflow-wrap:anywhere}
.case .meta{display:flex;gap:10px;flex-wrap:wrap;color:#839eb6;font-size:11px;margin:9px 0}
.case-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.case .muted,.draft .muted{line-height:1.5}
.tag{display:inline-flex;align-items:center;border:1px solid #3a5066;border-radius:100px;padding:5px 10px;color:#aec4d6;font-size:10px;font-weight:750;letter-spacing:.06em;white-space:nowrap}
.tag.verified{background:#0c342f;color:#79eaca;border-color:#347c6c}
.tag.test{background:#3a2e1b;color:#f9d28c;border-color:#806539}
.tag.danger{background:#442932;border-color:#864551;color:#ffafb2}
.tag.neutral{background:#243347;color:#b3c4d7}
label.field,.field{display:grid;gap:7px;color:#afc5d8;font-size:12px;font-weight:660}
input,select,textarea{width:100%;min-height:44px;color:#f1f8ff;background:#0c1c2c;border:1px solid #334c62;border-radius:11px;padding:11px 13px;outline:none}
input::placeholder,textarea::placeholder{color:#748ca4}
input:focus,select:focus,textarea:focus{border-color:var(--teal);box-shadow:0 0 0 3px #69e7cf1b}
textarea{min-height:96px;resize:vertical}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.draft .controls{grid-template-columns:repeat(2,minmax(0,1fr))}
.actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-top:12px}
.save{margin-top:12px}
.editor-disclosure{margin-top:17px;border-top:1px solid #32465a;padding-top:5px}
.editor-disclosure summary{list-style:none;cursor:pointer;color:var(--teal);font-size:12px;font-weight:760;display:flex;align-items:center;justify-content:space-between;padding:12px 0;outline-offset:4px}
.editor-disclosure summary::-webkit-details-marker{display:none}
.editor-disclosure summary:after{content:"+";color:var(--teal);font-weight:700;font-size:19px}
.editor-disclosure[open] summary:after{content:"−"}
.editor-disclosure .controls,.editor-disclosure label.field{margin:8px 0 12px}
.editor-disclosure .save{width:auto}
.empty{border:1px dashed #476174;background:#1124388c;border-radius:17px;padding:25px;color:#9ab2c7;line-height:1.6}
.empty strong{display:block;color:#e8f4ff;margin-bottom:6px}
.banner{padding:14px 17px;background:#322d279e;border:1px solid #695338;border-left:3px solid #e9b96d;border-radius:13px;color:#eed7ad;font-size:12px;line-height:1.65}
.ok{color:var(--teal)}
.error{color:var(--red)}
.hidden{display:none!important}
#flash{position:sticky;top:81px;z-index:38;margin:0 0 14px;padding:13px 17px;background:#173734;border:1px solid #419f87;border-radius:14px;color:#c0ffeb;font-weight:650;display:none;box-shadow:var(--shadow)}
#flash.error{background:#3d242e;border-color:#b95d6c;color:#ffc5ce}
.toolline{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0 18px}
#search{max-width:430px;flex:1 1 230px}
#case-count,#task-count{color:#8fa9bd;font-size:12px}
.filter-strip{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 18px}
.filter-strip button{background:#13283c;color:#b3c8da;border:1px solid #355067;border-radius:100px;padding:8px 13px;font-size:11px;min-height:36px}
.filter-strip button.active{color:#0e3135;background:#83eed8;border-color:#83eed8;font-weight:800}
.priority-row{display:flex;align-items:flex-start;gap:11px;padding:14px 0;border-bottom:1px solid #2b4156}
.priority-row:last-child{border-bottom:none}
.priority-number{display:grid;place-items:center;flex:none;width:30px;height:30px;border:1px solid #355f66;border-radius:10px;background:#174044;color:#86f4da;font-size:11px;font-weight:850}
.priority-row strong{display:block;color:#f1f7ff;font-size:13px;margin-bottom:3px}
.priority-row small{display:block;color:#8eabc0;line-height:1.45}
.priority-row button{min-height:35px;padding:6px 11px;font-size:11px;margin-left:auto;white-space:nowrap}
.mini-link{border:0;background:transparent;padding:6px;color:var(--teal);min-height:32px;font-size:12px}
.mini-link:hover{background:#1f3d45}
#urgent p{margin:8px 0}
#recent .case{padding:17px 19px}
#recent .case h3{font-size:15px}
#channels .box{box-shadow:none}
.source-meter{height:8px;border-radius:100px;background:#1c3448;margin:12px 0 6px;overflow:hidden}
.source-meter span{display:block;height:100%;border-radius:100px;background:linear-gradient(90deg,#40bdb9,#a2edcc)}
#channels .source-value{font-size:12px;color:#a4bfd1}
#task-list .case,#case-list .case{box-shadow:0 12px 26px #0003}
#task-list .case{border-left:3px solid #45616b}
#task-list .case.is-overdue{border-left-color:#eda96e}
#task-list .case.is-done{opacity:.85}
.finance-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.system-lines p{margin:0;padding:10px 0;border-bottom:1px solid #2b4256}
.system-lines p:last-child{border:0}
.mobile-dock,.more-sheet{display:none}
footer{margin-top:46px;padding-top:20px;border-top:1px solid #284155;color:#819ab2;font-size:11px;line-height:1.7}
@media(max-width:1160px){#metrics.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.two{grid-template-columns:1fr}}
@media(max-width:760px){
 header{padding:12px 16px;min-height:70px}
 .brand-emblem{width:36px;height:36px;font-size:20px}
 .brand{font-size:19px}
 .secure-label{display:none}
 .header-link{display:none}
 main{margin-left:0;padding:23px 15px 118px;max-width:710px}
 nav[aria-label="Workspace tabs"]{display:none}
 .mobile-dock{position:fixed;bottom:0;left:0;right:0;z-index:50;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));background:#0b192af2;border-top:1px solid #395367;padding:7px 7px max(9px,env(safe-area-inset-bottom));backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);box-shadow:0 -12px 28px #0005}
 .mobile-dock button{border:0;background:transparent;display:flex;flex-direction:column;gap:4px;align-items:center;justify-content:center;min-width:0;min-height:56px;padding:7px 2px;color:#91a9bd;border-radius:12px;font-size:10px;font-weight:760}
 .mobile-dock button .dock-icon{font-size:16px;line-height:1.1;color:#85a6b9}
 .mobile-dock button.active{color:#93ffdd;background:#193d43}
 .mobile-dock button.active .dock-icon{color:#77ebcc}
 .more-sheet{position:fixed;z-index:49;display:none;bottom:calc(80px + env(safe-area-inset-bottom));right:12px;width:min(300px,calc(100vw - 24px));background:#14273a;border:1px solid #3b596a;padding:12px;border-radius:18px;box-shadow:0 20px 60px #000a}
 .more-sheet.open{display:grid;gap:7px}
 .more-sheet button{width:100%;text-align:left;background:#1b3248;border-radius:12px;padding:13px}
 .more-sheet h3{padding:8px 9px 4px}
 .page-heading{margin-bottom:18px;display:block}
 .sync-indicator{display:inline-flex;margin-top:15px}
 .grid{gap:10px}
 .box,.case,.draft{padding:18px;border-radius:17px}
 .controls{grid-template-columns:repeat(2,minmax(0,1fr))}
 #metrics.grid{gap:10px}
 .tile{min-height:122px;padding:16px;border-radius:16px}
 .tile strong{font-size:34px}
 .tile .kpi-detail{font-size:10px}
 .two{gap:13px}
 #flash{top:76px}
}
@media(max-width:430px){
 h1{font-size:33px}
 h2{font-size:20px}
 .lead{font-size:13px}
 .controls,.draft .controls{grid-template-columns:1fr}
 .box,.case,.draft{padding:16px}
 .tile{min-height:118px;padding:14px}
 .tile strong{font-size:31px}
 .tile .label{font-size:11px}
 .priority-row{gap:7px}
 .priority-row button{padding:5px 8px}
 .toolline #search{max-width:none}
 .banner{padding:12px 13px}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.panel.active{animation:none}button{transition:none;transform:none}}
`;
