# Lead capture to CRM

Small service that takes web-form submissions, cleans them up, avoids duplicates and
saves them to a CRM, then pings the team in chat.

What it does with each submission:

1. Validates it. Needs a valid email or phone, otherwise the webhook answers 422 with the bad fields.
2. Normalizes it: lower-cased email, phone converted to +E.164, names tidied.
3. Looks for an existing contact by email, then by phone. A repeat submission updates that
   contact (it only fills blank fields) instead of creating a second one.
4. Adds tags: source, business or personal email, and "pricing" / "urgent" if the message says so.
5. Posts a message to a Slack-style webhook. If that fails the lead is still saved.

## Run it

Needs Python 3.10 or newer.

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:create_app --factory

Open http://localhost:8000 for a demo form and http://localhost:8000/leads to see the
contacts. Form tools can POST JSON or form data to `/webhook/lead`:

    curl -X POST localhost:8000/webhook/lead -H 'content-type: application/json' \
      -d '{"email":"jane@acme.com","name":"Jane Doe","message":"Need a quote asap"}'

Settings (environment variables): `CRM_BACKEND` (`sqlite` or `hubspot`), `CRM_DB_PATH`,
`HUBSPOT_TOKEN`, `NOTIFY_WEBHOOK_URL`, `DEFAULT_PHONE_REGION` (default `US`).

## Plugging in a real CRM

The SQLite CRM is a stand-in. A backend is a class with six methods, listed at the bottom of
`app/crm/base.py`. `app/crm/hubspot.py` is a working example of the HubSpot v3 API; set
`CRM_BACKEND=hubspot` and `HUBSPOT_TOKEN`. It has not been run against a live HubSpot account.
Another CRM means writing one more file like it and adding a line to `build_crm`.

## Tests

    pytest
