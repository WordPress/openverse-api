import pytest
import subprocess

from unittest import mock
from io import StringIO, BytesIO
import psycopg2
from django.db import connections
from django.core.management import call_command
from django.test.utils import CaptureQueriesContext

from catalog.api.models.audio import Audio, AudioAddOn

from test.factory.faker import WaveformProvider
from test.factory.models.audio import AudioFactory, AudioAddOnFactory


@mock.patch("catalog.api.models.audio.generate_peaks")
def call_generatewaveforms(mock_generate_peaks: mock.MagicMock) -> tuple[str, str]:
    mock_generate_peaks.side_effect = lambda _: WaveformProvider.generate_waveform()
    out = StringIO()
    err = StringIO()
    call_command("generatewaveforms", stdout=out, stderr=err)

    return out.getvalue(), err.getvalue()


def assert_all_audio_have_waveforms():
    assert list(
        AudioAddOn.objects.filter(waveform_peaks__isnull=False).values_list('audio_identifier')
     ).sort() == list(
         Audio.objects.all().values_list('identifier')
     ).sort()


@pytest.mark.django_db
def test_creates_waveforms_for_audio():
    AudioFactory.create_batch(153)

    assert AudioAddOn.objects.count() == 0

    call_generatewaveforms()

    assert_all_audio_have_waveforms()


@pytest.mark.django_db
def test_does_not_reprocess_existing_waveforms():
    waveformless_audio = AudioFactory.create_batch(3)

    # AudioAddOnFactory will create associated Audio objects as well
    # so those three will serve as the audio that should _not_ get processed
    waveforms = AudioAddOnFactory.create_batch(3)

    # Create an add on that doesn't have a waveform, this one should get processed as well
    null_waveform_addon = AudioAddOnFactory.create(waveform_peaks=None)
    waveformless_audio.append(Audio.objects.get(identifier=null_waveform_addon.audio_identifier))

    out, err = call_generatewaveforms()

    assert f"Generating waveforms for {len(waveformless_audio)} records" in out
    assert_all_audio_have_waveforms()


@pytest.mark.django_db
@mock.patch("catalog.api.models.audio.generate_peaks")
def test_paginates_audio_waveforms_to_generate(mock_generate_peaks, django_assert_num_queries):
    mock_generate_peaks.return_value = WaveformProvider.generate_waveform()

    audio_count = 53  # 6 pages
    pages = 6
    AudioFactory.create_batch(audio_count)

    test_audio = AudioFactory.create()
    with CaptureQueriesContext(connections['default']) as capture:
        test_audio.get_or_create_waveform()
    test_audio.delete()
    
    queries_per_iteration = len(capture.captured_queries)

    pagination_queries = pages + 1  # 1 per page + the final empty page's query
    count_queries = 1  # initializes the count for tqdm
    interation_queries = queries_per_iteration * audio_count  # queries inside get_or_create_waveform
    
    expected_queries = interation_queries + pagination_queries + count_queries

    with django_assert_num_queries(expected_queries):
        call_generatewaveforms()

    assert_all_audio_have_waveforms()


@pytest.mark.django_db
@mock.patch("catalog.api.models.audio.generate_peaks")
def test_logs_and_continues_if_waveform_generation_fails(mock_generate_peaks):
    audio_count = 23
    return_values = [
        subprocess.CalledProcessError(1, 'audiowaveform', stderr=b"This is an error string") if i == 9 else WaveformProvider.generate_waveform()
        for i in range(audio_count)
    ]
    mock_generate_peaks.side_effect = return_values
    AudioFactory.create_batch(audio_count)

    out = StringIO()
    err = StringIO()
    call_command("generatewaveforms", stdout=out, stderr=err)

    # import pdb; pdb.set_trace()
    failed_audio = Audio.objects.exclude(identifier__in=AudioAddOn.objects.values_list('audio_identifier', flat=True))

    assert failed_audio.count() == 1
    assert f"Unable to process {failed_audio.first().identifier}" in err.getvalue()

    assert AudioAddOn.objects.filter(waveform_peaks__isnull=False).count() == audio_count - 1
