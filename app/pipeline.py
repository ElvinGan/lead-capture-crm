import re

from .crm.base import Contact
from .normalize import normalize

FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "proton.me"}


def tags_for(lead):
    tags = [f"source:{lead.source}"]
    if lead.email:
        domain = lead.email.split("@")[1]
        tags.append("email:personal" if domain in FREE_MAIL else "email:business")
    else:
        tags.append("phone-only")
    text = lead.message or ""
    if re.search(r"\b(price|pricing|quote|cost|budget)\b", text, re.I):
        tags.append("intent:pricing")
    if re.search(r"\b(urgent|asap|this week)\b", text, re.I):
        tags.append("priority:urgent")
    return tags


def process_lead(raw, crm, notifier, default_region="US"):
    """Validate, dedupe on email then phone, create or update, tag, notify."""
    lead = normalize(raw, default_region)
    tags = tags_for(lead)
    fields = {k: getattr(lead, k) for k in ("email", "phone", "first_name", "last_name", "company")}

    existing = (lead.email and crm.find_by_email(lead.email)) or (lead.phone and crm.find_by_phone(lead.phone))
    if existing:
        # only fill gaps, so a sloppy second submission can't overwrite good data
        patch = {k: v for k, v in fields.items() if v and not getattr(existing, k)}
        patch["submissions"] = existing.submissions + 1
        contact = crm.update(existing.id, patch)
        crm.add_tags(contact.id, tags)
        action = "updated"
    else:
        contact = crm.create(Contact(id="", tags=tags, **fields))
        action = "created"

    crm.log_submission(contact.id, raw)
    status = notifier.send(contact, action, tags)
    return {"action": action, "contact_id": contact.id, "tags": tags, "notification": status}
