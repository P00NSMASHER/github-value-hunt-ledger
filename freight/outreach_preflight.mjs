/** Private reservation CLI. Deliberately contains no sending capability. */
import { readFileSync, realpathSync, openSync, closeSync, writeFileSync, renameSync, unlinkSync, fsyncSync } from "node:fs";
import { resolve, dirname, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { reserveOutreach } from "./outreach_guard.mjs";
const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const args=process.argv.slice(2);
if (args.length!==4) {
  console.error("Usage: node freight/outreach_preflight.mjs PRIVATE_MESSAGE.json PRIVATE_LEDGER.json PRIVATE_SENDER.json UNIQUE_RESERVATION_ID");
  process.exit(2);
}
let lock, lockPath, temp;
try {
  const paths=args.slice(0,3).map(p=>realpathSync(p));
  if (paths.some(p=>p===root || p.startsWith(root+sep))) throw new Error("PRIVATE_INPUTS_MUST_BE_OUTSIDE_CHECKOUT");
  lockPath=paths[1]+".lock";
  lock=openSync(lockPath,"wx",0o600);
  const message=JSON.parse(readFileSync(paths[0],"utf8"));
  const state=JSON.parse(readFileSync(paths[1],"utf8"));
  const sender=JSON.parse(readFileSync(paths[2],"utf8"));
  const result=reserveOutreach(message,state,sender,new Date().toISOString(),args[3]);
  if (!result.ok) {
    console.error(JSON.stringify({ok:false,errors:result.errors}));
    process.exitCode=1;
  } else {
    temp=paths[1]+".reserved-"+process.pid;
    const fd=openSync(temp,"wx",0o600);
    try { writeFileSync(fd,JSON.stringify(result.state,null,2)+"\n");fsyncSync(fd); } finally { closeSync(fd); }
    renameSync(temp,paths[1]);temp=undefined;
    console.log(JSON.stringify({ok:true,reserved:true,email_sent:false}));
  }
} catch (error) {
  console.error(JSON.stringify({ok:false,error:error.code==="EEXIST"?"LEDGER_LOCKED":error.message}));
  process.exitCode=1;
} finally {
  if (temp) { try { unlinkSync(temp); } catch {} }
  if (lock!==undefined) { closeSync(lock);unlinkSync(lockPath); }
}
