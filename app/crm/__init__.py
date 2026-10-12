import os

from .base import Contact
from .sqlite_crm import SQLiteCRM

__all__ = ["Contact", "SQLiteCRM", "build_crm"]


def build_crm():
    backend = os.getenv("CRM_BACKEND", "sqlite")
    if backend == "sqlite":
        return SQLiteCRM(os.getenv("CRM_DB_PATH", "crm.db"))
    if backend == "hubspot":
        from .hubspot import HubSpotCRM
        return HubSpotCRM(os.environ["HUBSPOT_TOKEN"])
    raise ValueError(f"unknown CRM_BACKEND {backend!r}")
