import uuid
from unittest import mock
from unittest.mock import Mock

import pytest
from catalog.api.models.audio import Audio, AudioAddOn


@pytest.fixture
@pytest.mark.django_db
def audio_fixture():
    audio = Audio(
        identifier=uuid.uuid4(),
    )

    audio.save()

    return audio


@pytest.mark.django_db
@mock.patch("requests.post")
def test_audio_waveform_caches(post, audio_fixture):
    mock_waveform = [0.4, 0.3, 0.1, 0, 1, 0.6]
    awf_res = {"peak_sets": {"1000": {"length": 6, "peaks": mock_waveform}}}
    post.return_value = Mock(json=Mock(return_value=awf_res))

    assert AudioAddOn.objects.count() == 0
    assert audio_fixture.get_or_create_waveform() == mock_waveform
    assert AudioAddOn.objects.count() == 1
    # Ensure the waveform was saved
    assert (
        AudioAddOn.objects.get(audio_identifier=audio_fixture.identifier).waveform_peaks
        == mock_waveform
    )
    assert audio_fixture.get_or_create_waveform() == mock_waveform
    # Should only be called once if Audio.get_or_create_waveform is using the DB value on subsequent calls
    post.assert_called_once()

    # Ensure there are no foreign constraints on the AudioAddOn that would cause failures during refresh
    audio_fixture.delete()

    assert AudioAddOn.objects.count() == 1
