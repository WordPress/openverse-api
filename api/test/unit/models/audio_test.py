import uuid
from unittest import mock

import pytest
from catalog.api.models.audio import Audio, AudioWaveformAddOn


@pytest.fixture
@pytest.mark.django_db
def audio_fixture():
    audio = Audio(
        identifier=uuid.uuid4(),
    )

    audio.save()

    return audio


@pytest.mark.django_db
@mock.patch("catalog.api.models.audio.generate_peaks")
def test_audio_waveform_caches(generate_peaks_mock, audio_fixture):
    mock_peaks = [0.4, 0.3, 0.1, 0, 1, 0.6]
    generate_peaks_mock.return_value = mock_peaks

    assert not hasattr(audio_fixture, "waveform")
    assert audio_fixture.get_or_create_waveform() == mock_peaks
    assert hasattr(audio_fixture, "waveform")
    assert audio_fixture.waveform.peaks == mock_peaks
    assert audio_fixture.get_or_create_waveform() == mock_peaks
    # Should only be called once if Audio.get_or_create_waveform is using the DB value on subsequent calls
    generate_peaks_mock.assert_called_once()

    # Ensure the waveform addon was saved
    waveform = AudioWaveformAddOn.objects.get(audio=audio_fixture)
    assert waveform.peaks == mock_peaks
