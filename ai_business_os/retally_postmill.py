"""RETALLY's private, synthetic, draft-only Postmill broker (public/v1)."""
import hashlib
import http.client
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

PIN = "b59d7ca3656836a8a8c8144dc3cde6a93070d083"
ACCOUNT = "retally-synthetic-instagram"
CHANNEL = "instagram-standalone"
CAMPAIGN = "retally_os_freight_pilot"
MEDIA = "freight/site/assets/brand/retally-wordmark-approved.png"
MEDIA_SHA = "08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd"
CALENDAR = "freight/brand/social/NOVEMBER_FIELD_NOTES_2026.md"
STAGES = ("idea", "draft", "review", "approved", "scheduled", "published", "failed")


@dataclass(frozen=True)
class Creative:
    title: str
    audience: str
    landing: str
    cta: str
    versions: tuple[str, ...]


# Only the public-source copy catalog can enter the pilot transport.
# New copy enters the catalog in a reviewed change. No CRM or case DTO is accepted.
CATALOG = {
    "liftgate_evidence": Creative("A liftgate line on the invoice", "Freight AP managers",
        "accessorial-charge-audit", "Save the accessorial evidence checklist.", (
            "A liftgate charge appears on an invoice. Compare the fee trigger in the agreement with the delivery record and check for an existing credit.",
            "Review a liftgate fee against the terms in effect on the shipment date. Match the service record to that shipment and check the credit history.")),
    "rate_version": Creative("Which rate sheet applied?", "Transportation buyers",
        "carrier-rate-audit", "Review the rate-version checklist.", (
            "Two rate sheets cover the same lane. The shipment date, contract language and effective amendments can establish which rate applies.",)),
    "prior_credits": Creative("Has the credit already posted?", "Controllers",
        "freight-audit-methodology", "Read the evidence checklist.", (
            "Match a proposed adjustment to the credit memo and the accounts-payable posting. A finding can remain open while the payment records are reconciled.",)),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def open_calendar(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS social_calendar (
            slug TEXT PRIMARY KEY, version INTEGER NOT NULL, stage TEXT NOT NULL,
            review_date TEXT NOT NULL, approval TEXT, remote_id TEXT, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS social_dispatch (
            binding TEXT PRIMARY KEY, slug TEXT NOT NULL, status TEXT NOT NULL,
            attempts INTEGER NOT NULL, remote_id TEXT, updated_at TEXT NOT NULL
        );
    """)
    return db


def seed_calendar(db):
    with db:
        for slug in CATALOG:
            db.execute("INSERT OR IGNORE INTO social_calendar VALUES(?,1,'draft',?,NULL,NULL,?)",
                       (slug, now(), now()))


def current(db, slug):
    row = db.execute("SELECT * FROM social_calendar WHERE slug=?", (slug,)).fetchone()
    if row is None:
        raise KeyError(slug)
    return dict(row)


def snapshot(row):
    slug = row["slug"]
    item = CATALOG[slug]
    destination = f"https://www.retallyrecovery.com/{item.landing}?" + urlencode({
        "utm_source": "instagram", "utm_medium": "organic_social", "utm_campaign": CAMPAIGN,
        "utm_content": slug,
    })
    return dict(slug=slug, account=ACCOUNT, channel=CHANNEL, version=row["version"],
                copy=item.versions[row["version"] - 1] + "\n\n" + item.cta,
                campaign=CAMPAIGN, destination=destination, time=row["review_date"],
                media=[dict(path=MEDIA, sha256=MEDIA_SHA, use="brand reference only")],
                attached_media=[], synthetic=True)


def growth_rows(db):
    rows = []
    for r in map(dict, db.execute("SELECT * FROM social_calendar ORDER BY slug")):
        snap = snapshot(r)
        readback = db.execute("SELECT remote_id, updated_at FROM social_dispatch "
                              "WHERE binding=? AND status='verified' AND remote_id=?",
                              (digest(snap), r["remote_id"])).fetchone()
        rows.append({**r, **snap, "remote_id": readback[0] if readback else None,
                     "readback_at": readback[1] if readback else None,
                     "title": CATALOG[r["slug"]].title, "audience": CATALOG[r["slug"]].audience,
                     "cta": CATALOG[r["slug"]].cta, "source_calendar": CALENDAR,
                     "channel_status": "unverified professional account",
                     "measured_reach": None, "publication_id": None})
    return rows


def revise(db, slug, version):
    if type(version) is not int or not 1 <= version <= len(CATALOG[slug].versions):
        raise ValueError("Select a catalog revision")
    with db:
        db.execute("UPDATE social_calendar SET version=?, stage='draft', approval=NULL, updated_at=? "
                   "WHERE slug=? AND version!=?", (version, now(), slug, version))


def review(db, slug, approve=False):
    """Record private editorial signoff. All live transport remains unavailable."""
    row = current(db, slug)
    old, new = ("review", "approved") if approve else ("draft", "review")
    sealed = digest(snapshot(row)) if approve else None
    with db:
        count = db.execute("UPDATE social_calendar SET stage=?, approval=?, updated_at=? "
                           "WHERE slug=? AND version=? AND stage=?",
                           (new, sealed, now(), slug, row["version"], old)).rowcount
    if not count:
        raise ValueError("Review stage or revision changed")


def check_publish(db, slug, binding):
    row = current(db, slug)
    if row["approval"] != digest(snapshot(row)) or row["approval"] != binding or row["stage"] != "approved":
        raise PermissionError("Approval expired or does not match this revision")
    raise PermissionError("Pilot has no publishing transport")


class PrivateDraftPort:
    """Loopback-only private backend. No redirects, proxy, uploads, arbitrary paths or generic writes."""
    def __init__(self, port, token):
        self.port = int(port)
        self._token = token

    @staticmethod
    def _valid_draft(data):
        if not isinstance(data, dict) or set(data) != {"type", "date", "shortLink", "tags", "posts"}:
            return False
        if data["type"] != "draft" or data["shortLink"] is not False or data["tags"] != []:
            return False
        if not isinstance(data["posts"], list) or len(data["posts"]) != 1:
            return False
        post = data["posts"][0]
        if not isinstance(post, dict) or set(post) != {"type", "integration", "value"}:
            return False
        if post["type"] != "draft" or post["integration"] != {"id": ACCOUNT}:
            return False
        if not isinstance(post["value"], list) or len(post["value"]) != 1:
            return False
        block = post["value"][0]
        copy = {version + "\n\n" + item.cta for item in CATALOG.values() for version in item.versions}
        return (isinstance(block, dict) and set(block) <= {"id", "content", "image"} and
                block.get("image") == [] and block.get("content") in copy)

    def _call(self, method, path, data=None, key=None):
        if method == "GET":
            route = urlsplit(path)
            allowed = path == "integrations" or (
                route.path == "posts" and not any((route.netloc, route.scheme, route.fragment))
                and set(parse_qs(route.query)) <= {"startDate", "endDate", "limit", "cursor"})
        else:
            allowed = method == "POST" and path == "posts" and self._valid_draft(data)
        if not allowed:
            raise PermissionError("Draft broker rejected method, route or content")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Authorization": self._token, "Content-Type": "application/json"}
        if key:
            headers["Idempotency-Key"] = key
        try:
            conn.request(method, "/public/v1/" + path, None if data is None else json.dumps(data), headers)
            response = conn.getresponse()
            if not 200 <= response.status < 300:
                self._error(method, path, response)
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise RuntimeError("Postmill readback exceeds the private pilot limit")
            return json.loads(body)
        finally:
            conn.close()

    def _error(self, method, path, response):
        raise RuntimeError(f"Postmill {method} {path.split('?')[0]} returned HTTP {response.status}")

    def assert_isolated(self):
        integrations = self._call("GET", "integrations")
        if (len(integrations) != 1 or integrations[0].get("id") != ACCOUNT or
                integrations[0].get("identifier") != CHANNEL or integrations[0].get("disabled") is not True):
            raise PermissionError("Requires a private org containing only the disabled fixture channel")

    def create_draft(self, row, key):
        item = snapshot(row)
        value = {"content": item["copy"], "image": []}
        if row["remote_id"]:
            value["id"] = row["remote_id"]  # pinned repository upserts on org + id
        post = {"type": "draft", "integration": {"id": ACCOUNT}, "value": [value]}
        data = {"type": "draft", "date": item["time"], "shortLink": False, "tags": [], "posts": [post]}
        return self._call("POST", "posts", data, key)

    def matching_ids(self, row):
        expected = snapshot(row)
        date = datetime.fromisoformat(expected["time"])
        params = {"startDate": (date - timedelta(minutes=1)).isoformat(),
                  "endDate": (date + timedelta(minutes=1)).isoformat(), "limit": 100}
        matches = []
        for _ in range(10):
            batch = self._call("GET", "posts?" + urlencode(params))
            for post in batch["posts"]:
                channel = post["integration"]
                if (channel["id"] == ACCOUNT and channel["providerIdentifier"] == CHANNEL and
                        post["state"] == "DRAFT" and post["content"] == expected["copy"] and
                        datetime.fromisoformat(post["publishDate"].replace("Z", "+00:00")) == date and
                        (not row["remote_id"] or post["id"] == row["remote_id"]) and
                        not post.get("releaseId") and not post.get("releaseURL") and not post.get("thumb")):
                    matches.append(post["id"])
            cursor = batch["cursor"]
            if cursor is None:
                if len(batch["posts"]) == 100 and params.get("cursor") == 900:
                    raise RuntimeError("Upstream row cap reached; reconcile manually")
                return matches
            if not isinstance(cursor, int) or cursor <= params.get("cursor", 0):
                break
            params["cursor"] = cursor
        raise RuntimeError("Incomplete Postmill readback")


def sync_draft(db, slug, port):
    """Claim before I/O. Even after timeout or a process crash, a replay can only read."""
    port.assert_isolated()
    row = current(db, slug)
    seal = digest(snapshot(row))
    with db:
        claimed = db.execute("INSERT OR IGNORE INTO social_dispatch VALUES(?,?,'pending',0,NULL,?)",
                             (seal, slug, now())).rowcount
    ids = port.matching_ids(row)
    if not ids and claimed:
        with db:
            db.execute("UPDATE social_dispatch SET attempts=attempts+1 WHERE binding=?", (seal,))
        try:
            reply = port.create_draft(row, seal)
            if len(reply) != 1 or reply[0].get("integration") != ACCOUNT or not reply[0].get("postId"):
                raise RuntimeError("Malformed Postmill draft receipt")
            expected_id = reply[0]["postId"]
        except (OSError, RuntimeError, ValueError, http.client.HTTPException):
            # A broken connection, 5xx or bad receipt can follow a committed write.
            expected_id = None
        ids = port.matching_ids(row)
        if expected_id and ids != [expected_id]:
            ids = []
    if len(ids) != 1:
        with db:
            db.execute("UPDATE social_dispatch SET status='hold',updated_at=? WHERE binding=? AND status!='verified'",
                       (now(), seal))
        raise RuntimeError("Draft readback absent or ambiguous; reconcile without resubmitting")
    with db:
        db.execute("UPDATE social_dispatch SET status='verified',remote_id=?,updated_at=? WHERE binding=?",
                   (ids[0], now(), seal))
        db.execute("UPDATE social_calendar SET remote_id=?,updated_at=? WHERE slug=? AND version=?",
                   (ids[0], now(), slug, row["version"]))
    return ids[0]


def checkpoint_drafts(db):
    """The only readback fields permitted to leave the isolated proof database."""
    result = []
    for slug in CATALOG:
        row = current(db, slug)
        binding = digest(snapshot(row))
        receipt = db.execute("SELECT * FROM social_dispatch WHERE binding=? AND status='verified' AND remote_id=?",
                             (binding, row["remote_id"])).fetchone()
        if not receipt:
            raise ValueError("Missing exact verified upstream receipt")
        result.append(dict(slug=slug, version=row["version"], review_date=row["review_date"],
                           binding=binding, remote_id=row["remote_id"], read_at=receipt["updated_at"],
                           draft_attempts=receipt["attempts"]))
    return result


def import_readback(db):
    """Import the bundled synthetic readback into a fresh owner desk. Performs no network I/O."""
    path = Path(__file__).with_name("postmill-draft-readback.json")
    proof = json.loads(path.read_text())
    if (proof["sha"] != PIN or proof["integration"] != ACCOUNT or not proof["disabled"] or
            proof["draft_writes_after_restart"] != 0 or proof["database_state_counts"] != "DRAFT|3" or
            {r["slug"] for r in proof["drafts"]} != set(CATALOG) or len(proof["drafts"]) != len(CATALOG)):
        raise ValueError("Unexpected pinned synthetic readback")
    with db:
        for row in proof["drafts"]:
            slug, post_id, seal = row["slug"], row["remote_id"], row["binding"]
            if (not 1 <= row["version"] <= len(CATALOG[slug].versions) or
                    digest(snapshot(row)) != seal or post_id != proof["draft_ids_after_restart"][slug]):
                raise ValueError("Readback does not match the current catalog")
            existing = db.execute("SELECT * FROM social_calendar WHERE slug=?", (slug,)).fetchone()
            if existing:
                if digest(snapshot(existing)) != seal or existing["remote_id"] != post_id:
                    raise ValueError("Existing draft differs; inspect the owner edits before importing")
                continue
            db.execute("INSERT INTO social_calendar VALUES(?,?,'draft',?,NULL,?,?)",
                       (slug, row["version"], row["review_date"], post_id, row["read_at"]))
            db.execute("INSERT INTO social_dispatch VALUES(?,?,'verified',?,?,?)",
                       (seal, slug, row["draft_attempts"], post_id, row["read_at"]))
    return len(proof["drafts"])
