import html
import json
import os
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .crm import build_crm
from .normalize import LeadError
from .notify import Notifier
from .pipeline import process_lead

STATIC = Path(__file__).resolve().parent.parent / "static"


async def read_payload(request):
    body = await request.body()
    if "application/json" in request.headers.get("content-type", ""):
        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError:
            raise HTTPException(400, "body is not valid JSON")
        if not isinstance(data, dict):
            raise HTTPException(400, "JSON body must be an object")
        return data
    return {k: v[-1] for k, v in parse_qs(body.decode()).items()}


def create_app(crm=None, notifier=None):
    crm = crm or build_crm()
    notifier = notifier or Notifier(os.getenv("NOTIFY_WEBHOOK_URL"), recorder=getattr(crm, "record_notification", None))
    region = os.getenv("DEFAULT_PHONE_REGION", "US")
    app = FastAPI(title="Lead capture to CRM")

    @app.post("/webhook/lead")
    async def webhook(request: Request):
        """For form tools (Typeform, Webflow, Zapier...). Accepts JSON or form-encoded."""
        data = await read_payload(request)
        try:
            return {"ok": True, **process_lead(data, crm, notifier, region)}
        except LeadError as e:
            return JSONResponse({"ok": False, "errors": e.errors}, status_code=422)

    @app.get("/", response_class=HTMLResponse)
    def form():
        return (STATIC / "form.html").read_text()

    @app.post("/submit")
    async def submit(request: Request):
        data = await read_payload(request)
        if data.get("website"):  # hidden honeypot field, only bots fill it
            return RedirectResponse("/?ok=1", status_code=303)
        try:
            process_lead(data, crm, notifier, region)
        except LeadError as e:
            return RedirectResponse("/?error=" + "+".join(e.errors), status_code=303)
        return RedirectResponse("/?ok=1", status_code=303)

    @app.get("/leads", response_class=HTMLResponse)
    def leads():
        if not hasattr(crm, "list_contacts"):
            raise HTTPException(404, "the contact list is only available on the SQLite backend")
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                *(html.escape(str(v or "")) for v in (
                    f"{c['first_name'] or ''} {c['last_name'] or ''}".strip(), c["company"], c["email"],
                    c["phone"], c["submissions"], ", ".join(c["tags"])))
            )
            for c in crm.list_contacts()
        )
        notes = "".join(
            f"<li><b>{html.escape(n['status'])}</b><pre>{html.escape(n['text'])}</pre></li>"
            for n in crm.list_notifications()
        )
        page = (STATIC / "leads.html").read_text()
        return page.replace("{{ROWS}}", rows or "<tr><td colspan=6>No leads yet</td></tr>").replace("{{NOTES}}", notes)

    return app

