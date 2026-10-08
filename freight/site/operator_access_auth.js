// Verified Cloudflare Access identity boundary for restricted RETALLY inquiry operators.
// Does not trust X-Forwarded-Email, form actor strings, or unsigned JWT payloads.
function fail() { throw new Error("operator_authentication_failed"); }
function segmentJson(segment) {
  if (typeof segment !== "string" || segment.length>8192 ||
      !/^[A-Za-z0-9_-]+$/.test(segment)) fail();
  try {
    const base64=segment.replace(/-/g,"+").replace(/_/g,"/");
    return JSON.parse(atob(base64.padEnd(Math.ceil(base64.length/4)*4,"=")));
  } catch { fail(); }
}
function decodeBytes(segment) {
  if (typeof segment!=="string" || segment.length>2048 ||
      !/^[A-Za-z0-9_-]+$/.test(segment)) fail();
  try {
    const x=atob(segment.replace(/-/g,"+").replace(/_/g,"/")
          .padEnd(Math.ceil(segment.length/4)*4,"="));
    return Uint8Array.from(x,c=>c.charCodeAt(0));
  } catch { fail(); }
}
function teamOrigin(value) {
  if(typeof value!=="string" || value.length>150) fail();
  let url;
  try {url=new URL(value);} catch {fail();}
  if(url.protocol!=="https:" || !/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(url.hostname) ||
     url.username || url.password || url.port || !["","/"].includes(url.pathname) ||
     url.search || url.hash) fail();
  return url.origin;
}
function allowedActors(value) {
  let list;
  try {list=JSON.parse(value);} catch {fail();}
  if(!Array.isArray(list) || list.length<1 || list.length>20)fail();
  for(const a of list) {
    if(!a || Object.keys(a).sort().join(",")!=="email,sub" ||
       typeof a.email!=="string" || a.email!==a.email.toLowerCase() ||
       !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(a.email) ||
       typeof a.sub!=="string" || a.sub.length<3 || a.sub.length>128)fail();
  }
  if(new Set(list.map(x=>x.sub)).size!==list.length)fail();
  return list;
}
export function configuredPolicy(env) {
  if(env?.RETALLY_CASE_WRITES_ENABLED!=="1" ||
     env?.RETALLY_CASE_POLICY_APPROVED!=="1" ||
     !env?.INQUIRY_DB?.prepare ||
     typeof env.RETALLY_ACCESS_AUD!=="string" ||
     !/^[0-9a-f]{20,80}$/i.test(env.RETALLY_ACCESS_AUD)) fail();
  const issuer=teamOrigin(env.RETALLY_ACCESS_TEAM_DOMAIN);
  const reviewers=allowedActors(env.RETALLY_INQUIRY_REVIEWERS);
  const approvers=allowedActors(env.RETALLY_INQUIRY_APPROVERS);
  if(!reviewers.length || !approvers.length)fail();
  return {issuer,aud:env.RETALLY_ACCESS_AUD,reviewers,approvers};
}
export async function verifyAccessJWT(request,env,fetcher=fetch) {
  const policy=configuredPolicy(env);
  const token=request.headers.get("Cf-Access-Jwt-Assertion");
  if(!token || token.length>12000)fail();
  const parts=token.split(".");
  if(parts.length!==3)fail();
  const header=segmentJson(parts[0]);
  const payload=segmentJson(parts[1]);
  if(!header || header.alg!=="RS256" ||
     typeof header.kid!=="string" || header.kid.length>256 || !header.kid)fail();
  const now=Math.floor(Date.now()/1000);
  if(!payload || payload.iss!==policy.issuer ||
     !Array.isArray(payload.aud) || !payload.aud.includes(policy.aud) ||
     !Number.isSafeInteger(payload.iat) ||
     !Number.isSafeInteger(payload.exp) ||
     payload.exp<=now || payload.iat>now+60 ||
     payload.exp-payload.iat>43200 ||
     (payload.nbf!==undefined && (!Number.isSafeInteger(payload.nbf)||payload.nbf>now)) ||
     typeof payload.sub!=="string" || payload.sub.length<3 || payload.sub.length>128 ||
     typeof payload.email!=="string" ||
     payload.email!==payload.email.toLowerCase()) fail();
  let response;
  try {
    response=await fetcher(policy.issuer+"/cdn-cgi/access/certs",
      {method:"GET",headers:{Accept:"application/json"},
       signal:AbortSignal.timeout(7000),redirect:"error",cache:"no-store"});
  }catch{fail();}
  if(!response?.ok)fail();
  let data;
  try {data=await response.json();}catch{fail();}
  if(!Array.isArray(data?.keys) || data.keys.length>12)fail();
  const jwk=data.keys.find(x=>x?.kid===header.kid && x?.kty==="RSA" &&
    (!x.alg || x.alg==="RS256") && (!x.use||x.use==="sig") &&
    x.e==="AQAB" && typeof x.n==="string" && x.n.length>=340);
  if(!jwk)fail();
  let valid=false;
  try {
    const key=await crypto.subtle.importKey("jwk",jwk,
      {name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
    valid=await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,
      decodeBytes(parts[2]),new TextEncoder().encode(parts[0]+"."+parts[1]));
  }catch{fail();}
  if(!valid)fail();
  return {sub:payload.sub,email:payload.email,policy};
}
export function hasRole(identity,role) {
  const list=role==="reviewer"?identity.policy.reviewers:
             role==="approver"?identity.policy.approvers:[];
  return list.some(x=>x.sub===identity.sub && x.email===identity.email);
}
