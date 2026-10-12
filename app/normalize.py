import re
from dataclasses import dataclass

import phonenumbers
from email_validator import EmailNotValidError, validate_email

# field names differ between form builders, so accept the common ones
ALIASES = {
    "email": ("email", "email_address", "your-email", "Email"),
    "phone": ("phone", "phone_number", "mobile", "tel", "Phone"),
    "first_name": ("first_name", "firstname", "fname", "First Name"),
    "last_name": ("last_name", "lastname", "lname", "Last Name"),
    "name": ("name", "full_name", "your-name", "Name"),
    "company": ("company", "company_name", "organization", "Company"),
    "message": ("message", "comments", "your-message", "Message"),
    "source": ("source", "form_name", "lead_source"),
}


class LeadError(ValueError):
    """Bad submission. .errors maps field name -> message."""

    def __init__(self, errors):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


@dataclass
class Lead:
    email: str | None
    phone: str | None
    first_name: str | None
    last_name: str | None
    company: str | None
    message: str | None
    source: str


def _pick(raw, key):
    for alias in ALIASES[key]:
        val = re.sub(r"\s+", " ", str(raw.get(alias) or "")).strip()
        if val:
            return val
    return None


def _name(value):
    # only fix names typed in all caps / all lowercase, leave "McDonald" alone
    if value and (value.isupper() or value.islower()):
        return value.title()
    return value


def normalize(raw, default_region="US"):
    errors = {}

    email = _pick(raw, "email")
    if email:
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError as e:
            errors["email"] = str(e)

    phone = _pick(raw, "phone")
    if phone:
        try:
            parsed = phonenumbers.parse(phone, default_region)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError
            phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except (phonenumbers.NumberParseException, ValueError):
            errors["phone"] = f"{phone!r} is not a valid phone number"

    if not errors and not (email or phone):
        errors["contact"] = "an email or a phone number is required"
    if errors:
        raise LeadError(errors)

    first, last = _pick(raw, "first_name"), _pick(raw, "last_name")
    full = _pick(raw, "name")
    if full and not (first or last):
        first, _, last = full.partition(" ")

    return Lead(
        email=email,
        phone=phone,
        first_name=_name(first),
        last_name=_name(last or None),
        company=_pick(raw, "company"),
        message=(_pick(raw, "message") or "")[:2000] or None,
        source=(_pick(raw, "source") or "website").lower(),
    )
