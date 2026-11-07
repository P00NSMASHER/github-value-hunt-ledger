"""Restricted loopback GopherCRM client for a single synthetic sales integration."""

import hashlib
import http.client
import ipaddress
import json
import math
import re
import time
from urllib.parse import urlencode, urlsplit


class CRMHold(RuntimeError):
    """Human review required. An empty or incomplete read is not permission to post."""


class CRMUnavailable(RuntimeError):
    """The read failed transiently, or the server explicitly throttled the request."""


class CRMThrottled(CRMUnavailable):
    """The pin rejected this request before its handler. No mutation occurred."""


class CRMAmbiguousWrite(RuntimeError):
    """The server might have committed the request. Reconcile by readback only."""


def _id(value):
    if type(value) is not int or value <= 0:
        raise CRMHold("invalid CRM record ID")
    return value


def _reference(value):
    if not isinstance(value, str) or not re.fullmatch(r"retally:synthetic:[A-Za-z0-9:._/-]{1,237}", value):
        raise CRMHold("invalid inquiry reference")
    return value


class GopherCRM:
    """Only the locally bound test service can receive this credential."""

    def __init__(self, base_url, api_key, owner_id, timeout=5):
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1")
                or url.username is not None or url.password is not None
                or url.path.rstrip("/") not in ("", "/api/v1") or url.query or url.fragment):
            raise ValueError("GopherCRM must use a literal HTTP loopback origin")
        self._host = str(ipaddress.ip_address(url.hostname))
        self._port = 80 if url.port is None else url.port
        if not isinstance(api_key, str) or not re.fullmatch(r"gcrm_[0-9a-fA-F]{64}", api_key):
            raise ValueError("expected a GopherCRM API key")
        self._key = api_key
        self.owner_id = _id(owner_id)
        if not self._port:
            raise ValueError("expected a nonzero loopback port")
        if not math.isfinite(timeout) or not 0 < timeout <= 30:
            raise ValueError("timeout must be between zero and 30 seconds")
        self._timeout = timeout
        self._identity_until = 0.0

    @property
    def base_url(self):
        host = f"[{self._host}]" if ":" in self._host else self._host
        return f"http://{host}:{self._port}"

    def _request(self, path, payload=None):
        # At this pin, authenticated requests refill at two per second. Only
        # read requests are retried here. The caller owns all write scheduling.
        for attempt in range(3):
            try:
                return self._request_once(path, payload)
            except CRMThrottled:
                if payload is not None or attempt == 2:
                    raise
                time.sleep(0.6 * (attempt + 1))

    def _request_once(self, path, payload=None):
        # Direct connection: no environment proxy, DNS lookup, redirects or automatic retries.
        conn = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
        write = payload is not None
        fault = CRMAmbiguousWrite if write else CRMUnavailable
        try:
            conn.request("POST" if write else "GET", "/api/v1" + path,
                         body=json.dumps(payload).encode() if write else None,
                         headers={"Authorization": "ApiKey " + self._key,
                                  "Accept": "application/json", "Content-Type": "application/json"})
            response = conn.getresponse()
            if response.status == 429:
                raise CRMThrottled("CRM throttled request before dispatch")
            if response.status >= 500 or response.status == 408:
                raise fault(f"CRM HTTP {response.status}")
            if response.status != (201 if write else 200):
                raise CRMHold(f"CRM refused request (HTTP {response.status})")
            content = response.read(2_000_001)
            if len(content) > 2_000_000:
                raise fault("CRM response exceeds size budget")
            data = json.loads(content)
            if not isinstance(data, dict) or data.get("success") is not True or not isinstance(data.get("data"), dict):
                raise fault("invalid CRM response envelope")
            return data["data"]
        except (OSError, http.client.HTTPException, ValueError) as error:
            raise fault("CRM response unavailable") from error
        finally:
            conn.close()

    def verify_identity(self):
        me = self._request("/users/me")
        if me.get("role") != "sales" or me.get("is_active") is not True or _id(me.get("id")) != self.owner_id:
            raise CRMHold("CRM requires the expected active sales user")
        self._identity_until = time.monotonic() + 3

    def _verify_read_identity(self):
        if time.monotonic() >= self._identity_until:
            self.verify_identity()

    def _check_lead(self, lead, external_id):
        if (not isinstance(lead, dict) or lead.get("external_id") != external_id
                or _id(lead.get("owner_id")) != self.owner_id):
            raise CRMHold("lead has unexpected identity or owner")
        return _id(lead.get("id"))

    def find_lead(self, external_id):
        self._verify_read_identity()
        data = self._request("/leads?" + urlencode({"external_id": _reference(external_id)}))
        rows = data.get("leads")
        if (not isinstance(rows, list) or type(data.get("total")) is not int
                or data["total"] != len(rows) or len(rows) > 1):
            raise CRMHold("ambiguous or incomplete lead lookup")
        return self._check_lead(rows[0], external_id) if rows else None

    def create_lead(self, external_id, fields):
        self.verify_identity()
        allowed = {"first_name", "last_name", "email", "phone", "company", "source", "classification"}
        if (not isinstance(fields, dict) or fields.keys() - allowed
                or any(not isinstance(v, str) for v in fields.values())):
            raise CRMHold("unapproved lead field")
        if fields.get("classification", "test") != "test":
            raise CRMHold("pilot requires synthetic classification")
        body = dict(fields, external_id=_reference(external_id), owner_id=self.owner_id, classification="test")
        row = self._request("/leads", body)
        return self._check_lead(row, external_id)

    @staticmethod
    def _task_title(external_id):
        marker = hashlib.sha256(_reference(external_id).encode()).hexdigest()
        return f"Qualify inquiry [RETALLY-{marker}]"

    def _check_task(self, task, title, lead_id):
        if (not isinstance(task, dict) or task.get("title") != title
                or _id(task.get("lead_id")) != lead_id or _id(task.get("assigned_to_id")) != self.owner_id):
            raise CRMHold("task has unexpected identity, lead or owner")
        return _id(task.get("id"))

    def find_task(self, external_id, lead_id):
        self._verify_read_identity()
        title, lead_id = self._task_title(external_id), _id(lead_id)
        # The pin ignores search filters for sales. Inspect complete bounded pages
        # before concluding absence. Drift, reassignment and duplicates require review.
        matches, seen, expected = [], set(), None
        for page in range(1, 6):
            data = self._request(f"/tasks/my?limit=100&page={page}")
            rows, total = data.get("tasks"), data.get("total")
            if (type(total) is not int or total < 0 or total > 500
                    or (expected is not None and total != expected) or not isinstance(rows, list)
                    or len(rows) != min(100, total - len(seen))):
                raise CRMHold("task inventory exceeds budget or changed during lookup")
            expected = total
            for task in rows:
                if not isinstance(task, dict) or _id(task.get("assigned_to_id")) != self.owner_id:
                    raise CRMHold("unexpected task owner")
                task_id = _id(task.get("id"))
                if task_id in seen:
                    raise CRMHold("duplicate task across pages")
                seen.add(task_id)
                if task.get("title") == title:
                    matches.append(self._check_task(task, title, lead_id))
            if len(seen) == total:
                break
        if len(matches) > 1:
            raise CRMHold("ambiguous qualification task")
        return matches[0] if matches else None

    def create_task(self, external_id, lead_id):
        self.verify_identity()
        title, lead_id = self._task_title(external_id), _id(lead_id)
        row = self._request("/tasks", {"title": title, "priority": "medium",
                                      "assigned_to_id": self.owner_id, "lead_id": lead_id})
        return self._check_task(row, title, lead_id)
