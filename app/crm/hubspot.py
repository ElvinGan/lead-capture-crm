"""HubSpot adapter (CRM v3 API). Same methods as SQLiteCRM, so CRM_BACKEND=hubspot swaps it in.

Needs a private-app token with contacts read/write and notes write. HubSpot contacts have
no tags, so tags go in a text property called lead_tags (create it in the portal first).
Not run against a live portal; the field mapping follows the public API docs.
"""
from datetime import datetime, timezone

import httpx

from .base import Contact

PROPS = {"email": "email", "phone": "phone", "first_name": "firstname",
         "last_name": "lastname", "company": "company"}
TAGS = "lead_tags"


class HubSpotCRM:
    name = "hubspot"

    def __init__(self, token, client=None):
        self.http = client or httpx.Client(base_url="https://api.hubapi.com", timeout=15)
        self.http.headers["Authorization"] = f"Bearer {token}"

    def _find(self, prop, value):
        r = self.http.post("/crm/v3/objects/contacts/search", json={
            "filterGroups": [{"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}],
            "properties": [*PROPS.values(), TAGS],
            "limit": 1,
        })
        r.raise_for_status()
        results = r.json()["results"]
        return self._contact(results[0]) if results else None

    def find_by_email(self, email):
        return self._find("email", email)

    def find_by_phone(self, phone):
        return self._find("phone", phone)

    def create(self, contact):
        props = {hs: getattr(contact, k) for k, hs in PROPS.items() if getattr(contact, k)}
        props[TAGS] = ";".join(contact.tags)
        r = self.http.post("/crm/v3/objects/contacts", json={"properties": props})
        r.raise_for_status()
        contact.id = r.json()["id"]
        return contact

    def update(self, contact_id, fields):
        props = {PROPS[k]: v for k, v in fields.items() if k in PROPS and v}
        r = self.http.patch(f"/crm/v3/objects/contacts/{contact_id}", json={"properties": props})
        r.raise_for_status()
        return self._contact(r.json())

    def add_tags(self, contact_id, tags):
        r = self.http.get(f"/crm/v3/objects/contacts/{contact_id}", params={"properties": TAGS})
        r.raise_for_status()
        current = (r.json()["properties"].get(TAGS) or "").split(";")
        merged = list(dict.fromkeys(t for t in [*current, *tags] if t))
        self.http.patch(f"/crm/v3/objects/contacts/{contact_id}",
                        json={"properties": {TAGS: ";".join(merged)}}).raise_for_status()

    def log_submission(self, contact_id, payload):
        body = "<br>".join(f"{k}: {v}" for k, v in payload.items())
        self.http.post("/crm/v3/objects/notes", json={
            "properties": {"hs_timestamp": datetime.now(timezone.utc).isoformat(),
                           "hs_note_body": "Web form submission<br>" + body},
            "associations": [{"to": {"id": contact_id}, "types": [
                {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]}],
        }).raise_for_status()

    def _contact(self, obj):
        p = obj["properties"]
        return Contact(id=str(obj["id"]), **{k: p.get(hs) for k, hs in PROPS.items()},
                       tags=[t for t in (p.get(TAGS) or "").split(";") if t])
