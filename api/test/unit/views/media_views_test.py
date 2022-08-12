import json
from http.client import HTTPResponse
from pathlib import Path
from test.factory.models.image import ImageFactory
from unittest import mock
from urllib.error import HTTPError

from rest_framework.test import APIClient

import pytest

from catalog.api.models.image import Image
from catalog.api.views.media_views import MediaViewSet


_MOCK_IMAGE_PATH = Path(__file__).parent / ".." / ".." / "factory"
_MOCK_IMAGE_BYTES = (_MOCK_IMAGE_PATH / "sample-image.jpg").read_bytes()
_MOCK_IMAGE_INFO = json.loads((_MOCK_IMAGE_PATH / "sample-image-info.json").read_text())


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def image() -> Image:
    return ImageFactory.create()


@pytest.mark.django_db
def test_thumb_error(api_client, image):
    error = None

    def urlopen_503_response(url, **kwargs):
        nonlocal error
        error = HTTPError(url, 503, "Bad error upstream whoops", {}, None)
        raise error

    with mock.patch(
        "catalog.api.views.media_views.urlopen"
    ) as urlopen_mock, mock.patch(
        "catalog.api.views.media_views.capture_exception", autospec=True
    ) as mock_capture_exception:
        urlopen_mock.side_effect = urlopen_503_response
        response = api_client.get(f"/v1/images/{image.identifier}/thumb/")

    assert response.status_code == 424
    mock_capture_exception.assert_called_once_with(error)


@pytest.mark.django_db
def test_thumb_sends_ua_header(api_client, image):
    with mock.patch("catalog.api.views.media_views.urlopen") as urlopen_mock:
        mock_res = mock.MagicMock(spec=HTTPResponse)
        mock_res.status = 200
        mock_res.headers = {}
        urlopen_mock.return_value = mock_res
        res = api_client.get(f"/v1/images/{image.identifier}/thumb/")

    assert res.status_code == 200

    urlopen_mock.assert_called_once()
    assert (
        urlopen_mock.call_args[0][0].headers["User-agent"]
        == MediaViewSet.THUMBNAIL_PROXY_COMM_HEADERS["User-Agent"]
    )
