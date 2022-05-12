from rest_framework import serializers

from catalog.api.constants.field_values import (
    ASPECT_RATIOS,
    IMAGE_CATEGORIES,
    IMAGE_SIZES,
)
from catalog.api.docs.media_docs import fields_to_md
from catalog.api.models import Image, ImageReport
from catalog.api.serializers.fields import EnumCharField
from catalog.api.serializers.media_serializers import (
    MediaSearchRequestSerializer,
    MediaSearchSerializer,
    MediaSerializer,
    get_hyperlinks_serializer,
    get_search_request_source_serializer,
)
from catalog.api.utils.url import add_protocol


#######################
# Request serializers #
#######################


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
        fields = ["identifier", "reason", "description"]
        read_only_fields = ["identifier"]

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


########################
# Response serializers #
########################

ImageHyperlinksSerializer = get_hyperlinks_serializer("image")


class ImageSerializer(ImageHyperlinksSerializer, MediaSerializer):
    """A single image. Used in search results."""

    class Meta:
        model = Image
        fields = [
            *MediaSerializer.Meta.fields,
            *ImageHyperlinksSerializer.field_names,
            "height",
            "width",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """


class ImageSearchSerializer(MediaSearchSerializer):
    """
    The full image search response.
    This serializer is purely representational and not actually used to
    serialize the response.
    """

    results = ImageSerializer(
        many=True,
        help_text=(
            "An array of images and their details such as "
            f"{fields_to_md(ImageSerializer.Meta.fields)}."
        ),
    )


##########################
# Additional serializers #
##########################


class OembedRequestSerializer(serializers.Serializer):
    """Parse and validate Oembed parameters."""

    url = serializers.CharField(
        help_text="The link to an image.",
    )

    @staticmethod
    def validate_url(value):
        return add_protocol(value)


class OembedSerializer(serializers.ModelSerializer):
    """The embedded content from a specified image URL."""

    version = serializers.ReadOnlyField(
        help_text="The image version.",
        default="1.0",
    )
    type = serializers.ReadOnlyField(
        help_text="Type of data.",
        default="photo",
    )
    width = serializers.SerializerMethodField(
        help_text="The width of the image in pixels."
    )
    height = serializers.SerializerMethodField(
        help_text="The height of the image in pixels."
    )
    title = serializers.CharField(help_text="The name of image.")
    author_name = serializers.CharField(
        help_text="The name of author for image.",
        source="creator",
    )
    author_url = serializers.URLField(
        help_text="A direct link to the author.",
        source="creator_url",
    )
    license_url = serializers.URLField(
        help_text="A direct link to the license for image."
    )

    class Meta:
        model = Image
        fields = [
            "version",
            "type",
            "width",
            "height",
            "title",
            "author_name",
            "author_url",
            "license_url",
        ]

    def get_width(self, obj) -> int:
        return self.context.get("width", obj.width)

    def get_height(self, obj) -> int:
        return self.context.get("height", obj.height)


class WatermarkRequestSerializer(serializers.Serializer):
    embed_metadata = serializers.BooleanField(
        help_text="Whether to embed ccREL metadata via XMP.", default=True
    )
    watermark = serializers.BooleanField(
        help_text="Whether to draw a frame around the image with attribution"
        " text at the bottom.",
        default=True,
    )
