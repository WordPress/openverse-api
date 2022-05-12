from rest_framework import serializers

from catalog.api.docs.media_docs import fields_to_md
from catalog.api.models import Image
from catalog.api.serializers.response.media import (
    MediaSearchSerializer,
    MediaSerializer,
    get_hyperlinks_serializer,
)


ImageHyperlinksSerializer = get_hyperlinks_serializer("image")  # class


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
