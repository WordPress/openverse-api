from rest_framework import serializers

from elasticsearch_dsl.response import Hit

from catalog.api.docs.media_docs import fields_to_md
from catalog.api.models import Audio, AudioSet
from catalog.api.serializers.fields import SchemableHyperlinkedIdentityField
from catalog.api.serializers.response.media import (
    MediaSearchSerializer,
    MediaSerializer,
    get_hyperlinks_serializer,
)


class AudioSetSerializer(serializers.ModelSerializer):
    """An audio set, rendered as a part of the ``AudioSerializer`` output."""

    class Meta:
        model = AudioSet
        fields = [
            "title",
            "foreign_landing_url",
            "creator",
            "creator_url",
            "url",
            "filesize",
            "filetype",
        ]


AudioHyperlinksSerializer = get_hyperlinks_serializer("audio")  # class


class AudioSerializer(AudioHyperlinksSerializer, MediaSerializer):
    """A single audio file. Used in search results."""

    class Meta:
        model = Audio
        fields = [  # keep this list ordered logically
            *MediaSerializer.Meta.fields,
            *AudioHyperlinksSerializer.field_names,
            "audio_set",
            "genres",
            "duration",
            "bit_rate",
            "sample_rate",
            "alt_files",
            "waveform",
            "peaks",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

    audio_set = AudioSetSerializer(
        required=False,
        help_text="Reference to set of which this track is a part.",
        read_only=True,
    )

    waveform = SchemableHyperlinkedIdentityField(
        read_only=True,
        view_name="audio-waveform",
        lookup_field="identifier",
        help_text="A direct link to the waveform peaks.",
    )

    # Add-on data
    peaks = serializers.SerializerMethodField(
        help_text="The list of peaks used to generate the waveform for the audio."
    )

    @staticmethod
    def get_peaks(obj) -> list[int]:
        if isinstance(obj, Hit):
            obj = Audio.objects.get(identifier=obj.identifier)
        return obj.get_waveform()


class AudioSearchSerializer(MediaSearchSerializer):
    """
    The full audio search response.
    This serializer is purely representational and not actually used to
    serialize the response.
    """

    results = AudioSerializer(
        many=True,
        help_text=(
            "An array of audios and their details such as "
            f"{fields_to_md(AudioSerializer.Meta.fields)}."
        ),
    )


class AudioWaveformSerializer(serializers.Serializer):
    len = serializers.SerializerMethodField()
    points = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=1)
    )

    @staticmethod
    def get_len(obj) -> int:
        return len(obj.get("points", []))
