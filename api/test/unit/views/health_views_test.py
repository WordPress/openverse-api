from unittest import mock

import pook
import pytest


def mock_health_response(status="green", timed_out=False):
    return (
        pook.get(pook.regex(r"_cluster\/health"))
        .times(1)
        .reply(200)
        .json(
            {
                "status": status if not timed_out else None,
                "timed_out": timed_out,
            }
        )
    )


@pytest.mark.django_db
def test_health_check_plain(api_client):
    res = api_client.get("/healthcheck/")
    assert res.status_code == 200


def test_health_check_calls__check_db(api_client):
    with mock.patch(
        "catalog.api.views.health_views.HealthCheck._check_db"
    ) as mock_check_db:
        res = api_client.get("/healthcheck/")
        assert res.status_code == 200
        mock_check_db.assert_called_once()


def test_health_check_es_timed_out(api_client):
    mock_health_response(timed_out=True)
    pook.on()
    res = api_client.get("/healthcheck/", data={"check_es": True})
    pook.off()

    assert res.status_code == 503
    assert res.json()["detail"] == "es_timed_out"


@pytest.mark.parametrize("status", ("yellow", "red"))
def test_health_check_es_status_bad(status, api_client):
    mock_health_response(status=status)
    pook.on()
    res = api_client.get("/healthcheck/", data={"check_es": True})
    pook.off()

    assert res.status_code == 503
    assert res.json()["detail"] == f"es_status_{status}"


@pytest.mark.django_db
def test_health_check_es_all_good(api_client):
    mock_health_response(status="green")
    pook.on()
    res = api_client.get("/healthcheck/", data={"check_es": True})
    pook.off()

    assert res.status_code == 200
