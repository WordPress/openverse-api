from api.catalog.api.models import image
from catalog.api.controllers.search_controller import get_sources
from catalog.api.docs.media_docs import fields_to_md
from catalog.api.models import Image, ImageReport
from catalog.api.serializers.media_serializers import (
    MediaSearchRequestSerializer,
    MediaSearchSerializer,
    MediaSerializer,
    _add_protocol,
    _validate_enum,
)
from rest_framework import serializers
from catalog.api.constants.categories import imageCategories


class ImageSearchRequestSerializer(MediaSearchRequestSerializer):
    """Parse and validate search query string parameters."""

    fields_names = [
        *MediaSearchRequestSerializer.fields_names,
        "source",
        "categories",
        "aspect_ratio",
        "size",
    ]
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    source = serializers.CharField(
        label="provider",
        help_text="A comma separated list of data sources to search. Valid "
        "inputs: "
        f"`{list(get_sources('image').keys())}`",
        required=False,
    )
    # Ref: ingestion_server/ingestion_server/categorize.py#Category
    categories = imageCategories
    aspect_ratio = serializers.CharField(
        label="aspect_ratio",
        help_text="A comma separated list of aspect ratios; available aspect "
        "ratios include `tall`, `wide`, and `square`.",
        required=False,
    )
    size = serializers.CharField(
        label="size",
        help_text="A comma separated list of image sizes; available sizes"
        " include `small`, `medium`, or `large`.",
        required=False,
    )

    @staticmethod
    def validate_source(input_sources):
        allowed_sources = list(get_sources("image").keys())
        input_sources = input_sources.split(",")
        input_sources = [x for x in input_sources if x in allowed_sources]
        input_sources = ",".join(input_sources)
        return input_sources.lower()

    @staticmethod
    def validate_categories(value):
        valid_categories = {"illustration", "digitized_artwork", "photograph"}
        _validate_enum("category", valid_categories, value)
        return value.lower()

    @staticmethod
    def validate_aspect_ratio(value):
        valid_ratios = {"tall", "wide", "square"}
        _validate_enum("aspect ratio", valid_ratios, value)
        return value.lower()


class ImageSerializer(MediaSerializer):
    """A single image. Used in search results."""

    fields_names = [
        *MediaSerializer.fields_names,
        "thumbnail",
        "height",
        "width",
        "detail_url",
        "related_url",
    ]
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    height = serializers.IntegerField(
        required=False,
        help_text="The height of the image in pixels. Not always available.",
    )
    width = serializers.IntegerField(
        required=False,
        help_text="The width of the image in pixels. Not always available.",
    )

    # Hyperlinks
    thumbnail = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name="image-thumb",
        lookup_field="identifier",
        help_text="A direct link to the miniature image.",
    )
    detail_url = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name="image-detail",
        lookup_field="identifier",
        help_text="A direct link to the detail view of this image.",
    )
    related_url = serializers.HyperlinkedIdentityField(
        view_name="image-related",
        lookup_field="identifier",
        read_only=True,
        help_text="A link to an endpoint that provides similar images.",
    )


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
            f"{fields_to_md(ImageSerializer.fields_names)}."
        ),
    )


class OembedRequestSerializer(serializers.Serializer):
    """Parse and validate Oembed parameters."""

    url = serializers.CharField(
        help_text="The link to an image.",
        required=True,
    )

    @staticmethod
    def validate_url(value):
        return _add_protocol(value)


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
