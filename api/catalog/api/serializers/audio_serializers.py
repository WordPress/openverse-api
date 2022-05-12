from rest_framework import serializers

from elasticsearch_dsl.response import Hit

from catalog.api.constants.field_values import AUDIO_CATEGORIES, DURATION
from catalog.api.docs.media_docs import fields_to_md
from catalog.api.models import AudioReport
from catalog.api.models.audio import Audio
from catalog.api.serializers.base import SchemableHyperlinkedIdentityField
from catalog.api.serializers.media_serializers import (
    MediaSearchRequestSerializer,
    MediaSearchSerializer,
    MediaSerializer,
    _validate_enum,
    get_hyperlinks_serializer,
    get_search_request_source_serializer,
)
from catalog.api.utils.help_text import make_comma_separated_help_text


class AudioSetSerializer(serializers.Serializer):
    """An audio set, rendered as a part of the ``AudioSerializer`` output."""

    title = serializers.CharField(help_text="The name of the media.", required=False)
    foreign_landing_url = serializers.URLField(
        required=False, help_text="A foreign landing link for the image."
    )

    creator = serializers.CharField(
        help_text="The name of the media creator.", required=False, allow_blank=True
    )
    creator_url = serializers.URLField(
        required=False, help_text="A direct link to the media creator."
    )

    url = serializers.URLField(help_text="The actual URL to the media file.")
    filesize = serializers.CharField(
        required=False, help_text="Number in bytes, e.g. 1024."
    )
    filetype = serializers.CharField(
        required=False,
        help_text="The type of the file, related to the file extension.",
    )


AudioSearchRequestSourceSerializer = get_search_request_source_serializer(
    "audio"
)  # class


class AudioSearchRequestSerializer(
    AudioSearchRequestSourceSerializer,
    MediaSearchRequestSerializer,
):
    """Parse and validate search query string parameters."""

    fields_names = [
        *MediaSearchRequestSerializer.fields_names,
        *AudioSearchRequestSourceSerializer.field_names,
        "category",
        "duration",
    ]
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    category = serializers.CharField(
        label="category",
        help_text=make_comma_separated_help_text(AUDIO_CATEGORIES, "categories"),
        required=False,
    )
    duration = serializers.CharField(
        label="duration",
        help_text=make_comma_separated_help_text(DURATION, "audio lengths"),
        required=False,
    )

    @staticmethod
    def validate_category(value):
        _validate_enum("category", AUDIO_CATEGORIES, value)
        return value.lower()

    @staticmethod
    def validate_duration(value):
        _validate_enum("duration", DURATION, value)
        return value.lower()


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


class AudioReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioReport
        fields = ("identifier", "reason", "description")
        read_only_fields = ("identifier",)

    def create(self, validated_data):
        if (
            validated_data["reason"] == "other"
            and (
                "description" not in validated_data
                or len(validated_data["description"])
            )
            < 20
        ):
            raise serializers.ValidationError(
                "Description must be at least be 20 characters long"
            )
        return AudioReport.objects.create(**validated_data)


class AudioWaveformSerializer(serializers.Serializer):
    len = serializers.SerializerMethodField()
    points = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=1)
    )

    @staticmethod
    def get_len(obj) -> int:
        return len(obj.get("points", []))
