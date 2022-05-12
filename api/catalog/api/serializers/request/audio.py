from rest_framework import serializers

from catalog.api.constants.field_values import AUDIO_CATEGORIES, DURATION
from catalog.api.models import AudioReport
from catalog.api.serializers.fields import EnumCharField
from catalog.api.serializers.request.media import (
    MediaSearchRequestSerializer,
    get_search_request_source_serializer,
)


AudioSearchRequestSourceSerializer = get_search_request_source_serializer("audio")


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

    category = EnumCharField(
        plural="categories",
        enum_var=AUDIO_CATEGORIES,
        required=False,
    )
    duration = EnumCharField(
        plural="durations",
        enum_var=DURATION,
        required=False,
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
