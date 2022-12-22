from rest_framework.test import APIClient
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def capture_exception(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("sentry_sdk.capture_exception", mock)

    yield mock
