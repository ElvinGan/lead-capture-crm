import logging

import httpx

log = logging.getLogger("notify")


class Notifier:
    """Posts a short message to a Slack-style incoming webhook (Slack, Teams and Google Chat all take {"text": ...})."""

    def __init__(self, webhook_url=None, client=None, recorder=None):
        self.webhook_url = webhook_url
        self.http = client or httpx.Client(timeout=10)
        self.recorder = recorder

    def send(self, contact, action, tags):
        name = " ".join(p for p in (contact.first_name, contact.last_name) if p) or "(no name)"
        label = "New lead" if action == "created" else "Returning lead"
        text = f"{label}: {name}\n{contact.email or ''} {contact.phone or ''}\nTags: {', '.join(tags)}"

        if not self.webhook_url:
            status = "logged"
            log.info(text)
        else:
            try:
                self.http.post(self.webhook_url, json={"text": text}).raise_for_status()
                status = "sent"
            except httpx.HTTPError as e:
                # the lead is already saved, so don't fail the request over a chat message
                status = "failed"
                log.warning("notification failed: %s", e)
        if self.recorder:
            self.recorder(contact.id, text, status)
        return status
