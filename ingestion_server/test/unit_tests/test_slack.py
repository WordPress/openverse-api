from unittest import mock

import pytest

from ingestion_server import slack


@pytest.mark.parametrize(
    "text, summary, expected_summary",
    [
        # Short text with default summary
        ("sample text", None, "sample text"),
        # Short text with explicit summary
        ("sample text", "different summary", "different summary"),
        # Multi-line text with default summary
        ("sample text\nLook a new line!", None, "Ingestion server message"),
        # Multi-line text with explicit summary
        ("sample text\nLook a new line!", "different summary", "different summary"),
    ],
)
@pytest.mark.parametrize(
    "webhook, should_alert",
    [
        # Actual webhook supplied
        ("http://fake", True),
        # No webhook supplied
        ("", False),
    ],
)
@pytest.mark.parametrize(
    "environment",
    [
        # Default environment
        None,
        # Different, explicit environment
        "staging",
    ],
)
def test_message(
    text,
    summary,
    webhook,
    should_alert,
    expected_summary,
    environment,
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv(slack.SLACK_WEBHOOK, webhook)
    with mock.patch("requests.post") as mock_post:
        slack._message(text, summary)
        assert mock_post.called == should_alert
        if not should_alert:
            return
        data = mock_post.call_args.kwargs["json"]
        assert data["blocks"][0]["text"]["text"] == text
        assert data["text"] == expected_summary
        if environment:
            assert data["username"].endswith(environment.upper())


@pytest.mark.parametrize(
    "log_func, log_level, should_log",
    [
        # Verbose logging
        (slack.verbose, "ERROR", False),
        (slack.verbose, "INFO", False),
        (slack.verbose, "VERBOSE", True),
        # Info logging
        (slack.info, "ERROR", False),
        (slack.info, "INFO", True),
        (slack.info, "VERBOSE", True),
        # Error logging
        (slack.error, "ERROR", True),
        (slack.error, "INFO", True),
        (slack.error, "VERBOSE", True),
        # If no log level set, verbose logging is enabled by default
        (slack.verbose, None, True),
        (slack.info, None, True),
        (slack.error, None, True),
    ],
)
def test_log_levels(log_func, log_level, should_log, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv(slack.SLACK_WEBHOOK, "http://fake")
    if log_level:
        monkeypatch.setenv(slack.LOG_LEVEL, log_level)
    with mock.patch("requests.post") as mock_post:
        log_func("text", "summary")
        assert mock_post.called == should_log
