from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from ai_business_os import retally_case_desk as desk
from ai_business_os.command_center_ui import csrf_token
from ai_business_os.retally_inquiry_sync import private_db
from ai_business_os.retally_pilot import freight_case
from ai_business_os.runtime_service import build_server


class PrivateDeskTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state=Path(self.root.name)/"desk.sqlite"
        self.ref="RA-20261107-1234CAFE"
        with private_db(self.state) as db:
            db.executescript(desk.SCHEMA)
            with db:
                db.execute("INSERT INTO identity VALUES(1,?,?,?,?)",("synthetic","fixture","local",2))
                db.execute("INSERT INTO delivery(seq,reference,fingerprint,service,accepted_at,phase,lead_id,task_id) VALUES(1,?,'fingerprint','freight',1,'done',1,1)",(self.ref,))
            desk.open_case(db,self.ref,"account:test","Operator","2026-11-10")

    def test_scoped_artifacts_and_stage_controls(self):
        with private_db(self.state) as db:
            doc={"fixture":True,"reference":self.ref,"source":"synthetic"}
            h=desk.add_artifact(db,self.ref,"fit",doc)
            with self.assertRaises(ValueError): desk.case_artifact(db,"account:other",self.ref,"fit",h)
            with self.assertRaises(ValueError): desk.advance(db,self.ref,"scoped")
            desk.update_task(db,self.ref,"Owner","2026-11-10","Missing evidence")
            with self.assertRaises(ValueError): desk.advance(db,self.ref,"qualified")
            desk.update_task(db,self.ref,"Owner","2026-11-10","")
            desk.advance(db,self.ref,"qualified")
            with self.assertRaises(ValueError): desk.advance(db,self.ref,"scoped")
            self.assertEqual(desk.customer_register(db)["engagements"][0]["stage"],"qualified")
            self.assertEqual(desk.case_artifact(db,"account:test",self.ref,"fit",h),doc)

    def test_replayed_fee_ledger(self):
        result,_=freight_case(self.ref)
        self.assertEqual(result["fee_sequence"],[0,12000,9000])
        self.assertEqual((result["flagged_cents"],result["recovery_cents"]),(100000,30000))

    def test_real_http_authorization_csrf_and_persistence(self):
        code="private-local-synthetic";secret="test-session-secret"
        with patch.dict(os.environ,{"PORT":"0","AIBOS_UI_ACCESS_SHA256":hashlib.sha256(code.encode()).hexdigest(),
                "AIBOS_UI_SESSION_SECRET":secret,"AIBOS_UI_PRINCIPAL":"Synthetic owner",
                "AIBOS_RETALLY_SYNTHETIC_DESK":str(self.state)}):
            server=build_server(pilot_only=True)
        self.assertEqual(server.server_address[0],"127.0.0.1")
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        def call(method,path,fields=None,cookie=None):
            conn=http.client.HTTPConnection(*server.server_address,timeout=4)
            headers={"Content-Type":"application/x-www-form-urlencoded"}
            if cookie: headers["Cookie"]=cookie
            conn.request(method,path,body=urlencode(fields) if fields else None,headers=headers)
            reply=conn.getresponse();body=reply.read().decode();conn.close()
            return reply,body
        self.assertEqual(call("GET","/ui/retally")[0].status,401)
        self.assertEqual(call("GET","/dashboard")[0].status,404)
        login,_=call("POST","/ui/login",{"access_code":code})
        self.assertEqual(login.status,303)
        cookie=login.getheader("Set-Cookie").split(";")[0]
        token=cookie.split("=",1)[1];details="/ui/retally?case="+self.ref
        response,body=call("GET",details,cookie=cookie)
        self.assertEqual(response.status,200);self.assertIn(self.ref,body)
        fields=dict(ref=self.ref,owner="Reassigned",due="2026-11-12",hold="Check invoice")
        self.assertEqual(call("POST","/ui/retally/triage",fields,cookie)[0].status,400)
        self.assertEqual(call("POST","/ui/retally/triage",{**fields,"csrf":csrf_token(token,secret)},cookie)[0].status,303)
        self.assertIn("Reassigned",call("GET",details,cookie=cookie)[1])
        self.assertEqual(call("POST","/ui/logout",{"csrf":csrf_token(token,secret)},cookie)[0].status,303)
        self.assertEqual(call("GET",details,cookie=cookie)[0].status,401)
        self.assertEqual(call("GET",details,cookie=cookie+"x")[0].status,401)
        self.assertEqual(call("POST","/approval/decide",{"decision":"approve"},cookie)[0].status,404)


if __name__=="__main__":
    unittest.main()
