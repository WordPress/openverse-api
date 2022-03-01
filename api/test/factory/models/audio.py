import factory
from factory.django import DjangoModelFactory

from test.factory.models.media import MediaFactory, IdentifierFactory
from test.factory.faker import Faker

from catalog.api.models.audio import Audio, AudioAddOn


class AudioFactory(MediaFactory):
    class Meta:
        model = Audio


class AudioAddOnFactory(DjangoModelFactory):
    class Meta:
        model = AudioAddOn
    
    audio_identifier = IdentifierFactory(AudioFactory)

    waveform_peaks = Faker("waveform")
