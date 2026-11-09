// Exact Cloudflare Access app, issuer, and hashed owner identity.
// A public, immutable audience ID is NOT an authentication secret.
export const ACCESS_AUD = '395437add099194675ac88c69a590bf6eefb587e54710ec436b99f50a4281594';
export const ACCESS_ISSUER = 'https://shy-surf-d83b.cloudflareaccess.com';
// Keep signed JWT lifetimes bounded to the Cloudflare Access app's 30-day session.
// The token still requires a matching issuer, audience, verified signature, and owner email.
// Cloudflare accepted 730-hour cookies before the owner reduced the app to 720 hours.
// Permit an already-issued, still-valid signed token within a strict 31-day cap.
const MAX_ACCESS_TOKEN_AGE_SECONDS = 31 * 24 * 60 * 60;
const OWNER_EMAIL_SHA256 = 'f5c62b72a196aec61d9e20ac302d5212b0eb407a433f1aa85d0f1ffd649df40a';
const fail = () => { throw new Error('owner_access_denied'); };
function decode(segment, limit=9000) {
  if (typeof segment !== 'string' || !segment || segment.length > limit || !/^[\w-]+$/.test(segment)) fail();
  try {
    const base64 = segment.replace(/-/g,'+').replace(/_/g,'/');
    return atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, '='));
  } catch { fail(); }
}
function json(segment) { try { return JSON.parse(decode(segment)); } catch { fail(); } }
function bytes(segment) { return Uint8Array.from(decode(segment,3000), x=>x.charCodeAt(0)); }
async function sha256(value) {
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export async function verifyRetallyOwner(request,fetcher=fetch,ownerDigest=OWNER_EMAIL_SHA256) {
  // Some browser-originated Pages requests may carry the signed Access application
  // token only as CF_Authorization. Prefer the origin assertion when present.
  // The cookie does not authorize anything by itself: it is fully verified below.
  const assertion=request.headers.get('Cf-Access-Jwt-Assertion');
  let token=assertion;
  if (token===null) {
    const raw=request.headers.get('Cookie');
    if (typeof raw!=='string' || raw.length>16384) fail();
    const matches=raw.split(';').map(x=>x.trim()).filter(x=>x.startsWith('CF_Authorization='));
    if (matches.length!==1) fail();
    token=matches[0].slice('CF_Authorization='.length);
  }
  if (!token || token.length > 12000) fail();
  const parts=token.split('.'); if (parts.length!==3) fail();
  const header=json(parts[0]),payload=json(parts[1]);
  if (!header || header.alg!=='RS256' || typeof header.kid!=='string' ||
      !/^[\w-]{1,256}$/.test(header.kid)) fail();
  const now=Math.floor(Date.now()/1000);
  if (!payload || payload.iss!==ACCESS_ISSUER || !Array.isArray(payload.aud) ||
      !payload.aud.includes(ACCESS_AUD) || !Number.isSafeInteger(payload.iat) ||
      !Number.isSafeInteger(payload.exp) || payload.exp<=now ||
      payload.iat>now+60 || payload.exp-payload.iat>MAX_ACCESS_TOKEN_AGE_SECONDS ||
      typeof payload.sub!=='string' || payload.sub.length<3 || payload.sub.length>128 ||
      typeof payload.email!=='string' || payload.email!==payload.email.trim().toLowerCase() ||
      payload.email.length>160 || !payload.email.includes('@') ||
      (payload.nbf!==undefined && (!Number.isSafeInteger(payload.nbf)||payload.nbf>now))) fail();
  if (await sha256(payload.email)!==ownerDigest) fail();
  let res,keys;
  try {
    res=await fetcher(ACCESS_ISSUER+'/cdn-cgi/access/certs',{
      method:'GET',headers:{Accept:'application/json'},
      signal:AbortSignal.timeout(7000),redirect:'error',cache:'no-store'
    });
    if (!res.ok) fail();
    const data=await res.json();
    keys=data.keys;
  } catch { fail(); }
  if (!Array.isArray(keys)||keys.length>20) fail();
  const jwk=keys.find(k=>k?.kid===header.kid && k.kty==='RSA' &&
    (!k.alg || k.alg==='RS256') && (!k.use || k.use==='sig') &&
    k.e==='AQAB' && typeof k.n==='string' && k.n.length>=340);
  if (!jwk) fail();
  let verified=false;
  try {
    const k=await crypto.subtle.importKey('jwk',jwk,
      {name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
    verified=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',k,
      bytes(parts[2]),new TextEncoder().encode(parts[0]+'.'+parts[1]));
  } catch { fail(); }
  if (!verified) fail();
  return {sub:payload.sub}; // Do not return PII or the underlying JWT.
}
