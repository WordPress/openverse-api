"""
Ensures that deprecated URLs are redirected to their updated paths and not left to rot.

Can be used to verify a live deployment is functioning as designed.
Run with the `pytest -s` command from this directory.
"""

import uuid
from test.constants import API_URL

from django.urls import reverse

import requests


def test_old_stats_endpoint():
    response = requests.get(
        f"{API_URL}{reverse('about-image')}?type=images",
        allow_redirects=False,
        verify=False,
    )
    assert response.status_code == 301
    assert response.is_permanent_redirect
    assert response.headers.get("Location") == reverse("image-stats")


def test_old_related_images_endpoint():
    idx = uuid.uuid4()
    response = requests.get(
        f"{API_URL}{reverse('related-images', identifier=idx)}",
        allow_redirects=False,
        verify=False,
    )
    assert response.status_code == 301
    assert response.is_permanent_redirect
    assert response.headers.get("Location") == reverse("image-related", identifier=idx)


def test_old_oembed_endpoint():
    response = requests.get(
        f"{API_URL}{reverse('oembed')}?key=value", allow_redirects=False, verify=False
    )
    assert response.status_code == 301
    assert response.is_permanent_redirect
    assert response.headers.get("Location") == f"{reverse('image-oembed')}?key=value"


def test_old_thumbs_endpoint():
    idx = uuid.uuid4()
    response = requests.get(
        f"{API_URL}{reverse('thumbs', identifier=idx)}",
        allow_redirects=False,
        verify=False,
    )
    assert response.status_code == 301
    assert response.is_permanent_redirect
    assert response.headers.get("Location") == reverse(
        "image-thumbnail", identifier=idx
    )
