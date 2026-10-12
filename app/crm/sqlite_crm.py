import json
import sqlite3
import uuid
from datetime import datetime, timezone

from .base import Contact

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    phone TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    submissions INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    text TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TEXT NOT NULL
);
"""

FIELDS = ("email", "phone", "first_name", "last_name", "company", "submissions")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SQLiteCRM:
    """Local stand-in for a CRM so the whole flow runs without any accounts."""

    name = "sqlite"

    def __init__(self, path="crm.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def _contact(self, row):
        if row is None:
            return None
        d = dict(row)
        return Contact(**{k: d[k] for k in ("id", *FIELDS)}, tags=json.loads(d["tags"]))

    def get(self, contact_id):
        return self._contact(self.db.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone())

    def find_by_email(self, email):
        return self._contact(self.db.execute("SELECT * FROM contacts WHERE email = ?", (email,)).fetchone())

    def find_by_phone(self, phone):
        return self._contact(self.db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,)).fetchone())

    def create(self, contact):
        contact.id = uuid.uuid4().hex[:10]
        with self.db:
            self.db.execute(
                "INSERT INTO contacts (id, email, phone, first_name, last_name, company, tags, submissions, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (contact.id, contact.email, contact.phone, contact.first_name, contact.last_name,
                 contact.company, json.dumps(contact.tags), contact.submissions, now()),
            )
        return contact

    def update(self, contact_id, fields):
        fields = {k: v for k, v in fields.items() if k in FIELDS and v is not None}
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            with self.db:
                self.db.execute(f"UPDATE contacts SET {sets}, updated_at = ? WHERE id = ?",
                                (*fields.values(), now(), contact_id))
        return self.get(contact_id)

    def add_tags(self, contact_id, tags):
        merged = list(dict.fromkeys([*self.get(contact_id).tags, *tags]))
        with self.db:
            self.db.execute("UPDATE contacts SET tags = ? WHERE id = ?", (json.dumps(merged), contact_id))

    def log_submission(self, contact_id, payload):
        with self.db:
            self.db.execute("INSERT INTO submissions (contact_id, payload, received_at) VALUES (?,?,?)",
                            (contact_id, json.dumps(payload), now()))

    # used by the demo pages
    def record_notification(self, contact_id, text, status):
        with self.db:
            self.db.execute("INSERT INTO notifications (contact_id, text, status, sent_at) VALUES (?,?,?,?)",
                            (contact_id, text, status, now()))

    def list_contacts(self):
        rows = self.db.execute("SELECT * FROM contacts ORDER BY updated_at DESC").fetchall()
        return [{**dict(r), "tags": json.loads(r["tags"])} for r in rows]

    def list_notifications(self, limit=10):
        return [dict(r) for r in self.db.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))]
