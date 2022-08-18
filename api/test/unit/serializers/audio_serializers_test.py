import uuid
from unittest.mock import MagicMock

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

import pytest

from catalog.api.serializers.audio_serializers import AudioSerializer


@pytest.fixture
def req():
    factory = APIRequestFactory()
    request = factory.get("/")
    request = Request(request)
    return request


@pytest.fixture
@pytest.mark.django_db
def audio_hit():
    hit = MagicMock(
        identifier=uuid.uuid4(),
        license="cc0",
        license_version="1.0",
    )
    return hit


@pytest.mark.django_db
def test_audio_serializer_adds_license_url_if_missing(req, audio_hit):
    # Note that this behaviour is inherited from the parent `MediaSerializer` class, but
    # it cannot be tested without a concrete model to test with.

    del audio_hit.license_url
    repr = AudioSerializer(audio_hit, context={"request": req}).data
    assert repr["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/"
