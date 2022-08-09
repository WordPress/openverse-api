from test.factory.models.oauth2 import AccessTokenFactory

from django.conf import settings
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

import pytest

from catalog.api.serializers.media_serializers import MediaSearchRequestSerializer


# TODO: @sarayourfriend consolidate these with the other
# request factory fixtures into conftest.py
@pytest.fixture
def request_factory() -> APIRequestFactory():
    request_factory = APIRequestFactory(defaults={"REMOTE_ADDR": "192.0.2.1"})

    return request_factory


@pytest.fixture
def access_token():
    token = AccessTokenFactory.create()
    token.application.verified = True
    token.application.save()
    return token


@pytest.fixture
def authed_request(access_token, request_factory):
    request = request_factory.get("/")

    force_authenticate(request, token=access_token.token)

    return APIView().initialize_request(request)


@pytest.fixture
def anon_request(request_factory):
    return APIView().initialize_request(request_factory.get("/"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("page_size", "authenticated"),
    (
        pytest.param(-1, False, marks=pytest.mark.raises(exception=ValidationError)),
        pytest.param(0, False, marks=pytest.mark.raises(exception=ValidationError)),
        (1, False),
        (settings.MAX_ANONYMOUS_PAGE_SIZE, False),
        pytest.param(
            settings.MAX_ANONYMOUS_PAGE_SIZE + 1,
            False,
            marks=pytest.mark.raises(exception=NotAuthenticated),
        ),
        pytest.param(
            settings.MAX_AUTHED_PAGE_SIZE,
            False,
            marks=pytest.mark.raises(exception=NotAuthenticated),
        ),
        pytest.param(-1, True, marks=pytest.mark.raises(exception=ValidationError)),
        pytest.param(0, True, marks=pytest.mark.raises(exception=ValidationError)),
        (1, True),
        (settings.MAX_ANONYMOUS_PAGE_SIZE + 1, True),
        (settings.MAX_AUTHED_PAGE_SIZE, True),
        pytest.param(
            settings.MAX_AUTHED_PAGE_SIZE + 1,
            True,
            marks=pytest.mark.raises(exception=ValidationError),
        ),
    ),
)
def test_page_size_validation(page_size, authenticated, anon_request, authed_request):
    request = authed_request if authenticated else anon_request
    serializer = MediaSearchRequestSerializer(
        context={"request": request}, data={"page_size": page_size}
    )
    serializer.is_valid(raise_exception=True)
