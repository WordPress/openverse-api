from catalog.api.views.audio_views import (
    AudioArt,
    AudioDetail,
    AudioStats,
    AudioWaveform,
    RelatedAudio,
    SearchAudio,
)
from django.urls import path


urlpatterns = [
    path("stats", AudioStats.as_view(), name="audio-stats"),
    path("<str:identifier>", AudioDetail.as_view(), name="audio-detail"),
    path("<str:identifier>/thumb", AudioArt.as_view(), name="audio-thumb"),
    path(
        "<str:identifier>/recommendations", RelatedAudio.as_view(), name="audio-related"
    ),
    path("<str:identifier>/waveform", AudioWaveform.as_view(), name="audio-waveform"),
    path("", SearchAudio.as_view(), name="audio"),
]
