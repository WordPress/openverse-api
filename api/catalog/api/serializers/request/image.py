from rest_framework import serializers

from catalog.api.constants.field_values import (
    ASPECT_RATIOS,
    IMAGE_CATEGORIES,
    IMAGE_SIZES,
)
from catalog.api.models import ImageReport
from catalog.api.serializers.base import EnumCharField
from catalog.api.serializers.request.media import (
    MediaSearchRequestSerializer,
    get_search_request_source_serializer,
)
from catalog.api.utils.url import add_protocol


ImageSearchRequestSourceSerializer = get_search_request_source_serializer("image")


class ImageSearchRequestSerializer(
    ImageSearchRequestSourceSerializer,
    MediaSearchRequestSerializer,
):
    """Parse and validate search query string parameters."""

    fields_names = [
        *MediaSearchRequestSerializer.fields_names,
        *ImageSearchRequestSourceSerializer.field_names,
        "category",
        "aspect_ratio",
        "size",
    ]
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    # Ref: ingestion_server/ingestion_server/categorize.py#Category
    category = EnumCharField(
        plural="categories",
        enum_var=IMAGE_CATEGORIES,
        required=False,
    )
    aspect_ratio = EnumCharField(
        plural="aspect ratios",
        enum_var=ASPECT_RATIOS,
        required=False,
    )
    size = EnumCharField(
        plural="image sizes",
        enum_var=IMAGE_SIZES,
        required=False,
    )


class ImageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageReport
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
        return ImageReport.objects.create(**validated_data)


class OembedRequestSerializer(serializers.Serializer):
    """Parse and validate Oembed parameters."""

    url = serializers.CharField(
        help_text="The link to an image.",
        required=True,
    )

    @staticmethod
    def validate_url(value):
        return add_protocol(value)


class WatermarkRequestSerializer(serializers.Serializer):
    embed_metadata = serializers.BooleanField(
        help_text="Whether to embed ccREL metadata via XMP.", default=True
    )
    watermark = serializers.BooleanField(
        help_text="Whether to draw a frame around the image with attribution"
        " text at the bottom.",
        default=True,
    )
