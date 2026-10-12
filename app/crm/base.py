from dataclasses import dataclass, field


@dataclass
class Contact:
    id: str
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    tags: list[str] = field(default_factory=list)
    submissions: int = 1


# A CRM backend needs these methods (see sqlite_crm.py for the reference version):
#   find_by_email(email) -> Contact | None
#   find_by_phone(phone) -> Contact | None
#   create(contact) -> Contact            (returns it with the CRM's id)
#   update(contact_id, fields) -> Contact (patch only, never blank existing data)
#   add_tags(contact_id, tags)
#   log_submission(contact_id, payload)   (keep the raw form data as a note)
