import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.normalize import LeadError, normalize
from app.pipeline import process_lead


def test_normalize_cleans_fields():
    lead = normalize({"Email": " Jane.Doe@Example.COM ", "phone": "(415) 555-2671", "name": "JANE DOE"})
    assert lead.email == "jane.doe@example.com"
    assert lead.phone == "+14155552671"
    assert (lead.first_name, lead.last_name) == ("Jane", "Doe")


@pytest.mark.parametrize("raw", [
    {"email": "not-an-email"},
    {"email": "a@example.com", "phone": "12"},
    {"name": "No Contact Details"},
])
def test_bad_submissions_are_rejected(raw):
    with pytest.raises(LeadError):
        normalize(raw)


def test_same_email_updates_instead_of_duplicating(crm, notifier):
    first = process_lead({"email": "sam@acme.com", "first_name": "Sam"}, crm, notifier)
    second = process_lead({"email": "SAM@acme.com", "phone": "415 555 2671", "company": "Acme"}, crm, notifier)
    assert (first["action"], second["action"]) == ("created", "updated")
    assert first["contact_id"] == second["contact_id"]
    contacts = crm.list_contacts()
    assert len(contacts) == 1
    assert contacts[0]["phone"] == "+14155552671"
    assert contacts[0]["submissions"] == 2


def test_phone_match_does_not_overwrite_existing_data(crm, notifier):
    process_lead({"email": "kim@acme.com", "phone": "415 555 2671", "first_name": "Kim"}, crm, notifier)
    process_lead({"phone": "+1 415 555 2671", "first_name": "KIMBERLY"}, crm, notifier)
    contacts = crm.list_contacts()
    assert len(contacts) == 1
    assert contacts[0]["first_name"] == "Kim"


def test_webhook_creates_lead_and_returns_422_on_bad_input(crm, notifier):
    client = TestClient(create_app(crm=crm, notifier=notifier))
    ok = client.post("/webhook/lead", json={"email": "lee@acme.com", "message": "Need a quote asap"})
    assert ok.status_code == 200
    assert {"intent:pricing", "priority:urgent"} <= set(ok.json()["tags"])
    bad = client.post("/webhook/lead", json={"email": "nope"})
    assert bad.status_code == 422 and "email" in bad.json()["errors"]
