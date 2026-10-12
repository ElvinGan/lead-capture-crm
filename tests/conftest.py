import pytest

from app.crm import SQLiteCRM
from app.notify import Notifier


@pytest.fixture
def crm(tmp_path):
    return SQLiteCRM(str(tmp_path / "crm.db"))


@pytest.fixture
def notifier(crm):
    # no webhook url, so notifications are just logged and recorded
    return Notifier(None, recorder=crm.record_notification)
