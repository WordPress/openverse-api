from rest_framework import serializers

from catalog.api.models.media import AbstractMedia
from catalog.api.serializers.base import SchemableHyperlinkedIdentityField
from catalog.api.serializers.response.tag import TagSerializer
from catalog.api.utils.url import add_protocol


class MediaSearchSerializer(serializers.Serializer):
    """
    This serializer serializes the full media search response. The class should
    be inherited by all individual media serializers.
    """

    result_count = serializers.IntegerField(
        help_text="The total number of items returned by search result.",
    )
    page_count = serializers.IntegerField(
        help_text="The total number of pages returned by search result.",
    )
    page_size = serializers.IntegerField(
        help_text="The number of items per page.",
    )
    page = serializers.IntegerField(
        help_text="The current page number returned in the response.",
    )
    # ``results`` field added by child serializers


class MediaSerializer(serializers.ModelSerializer):
    """
    This serializer serializes a single media file. The class should be
    inherited by all individual media serializers.
    """

    class Meta:
        model = AbstractMedia
        fields = [  # keep this list ordered logically
            "id",
            "title",
            "foreign_landing_url",
            "url",
            "creator",
            "creator_url",
            "filesize",
            "filetype",
            "license",
            "license_version",
            "license_url",  # property
            "provider",
            "source",
            "category",
            "tags",
            "mature",
            "attribution",  # property
            "thumbnail",
            "fields_matched",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

    id = serializers.CharField(
        help_text="Our unique identifier for an open-licensed work.",
        source="identifier",
    )

    tags = TagSerializer(
        allow_null=True,  # replaced with ``[]`` later
        many=True,
        help_text="Tags with detailed metadata, such as accuracy.",
    )

    fields_matched = serializers.ListField(
        allow_null=True,  # replaced with ``[]`` later
        help_text="List the fields that matched the query for this result.",
    )

    mature = serializers.BooleanField(
        required=False,  # present in ``Hit`` but not in Django media models
        help_text="Whether the media item is marked as mature",
    )

    def to_representation(self, *args, **kwargs):
        output = super().to_representation(*args, **kwargs)

        # Ensure lists are ``[]`` instead of ``None``
        # TODO: These fields are still marked 'Nullable' in the API docs
        list_fields = ["tags", "fields_matched"]
        for list_field in list_fields:
            if output[list_field] is None:
                output[list_field] = []

        # Ensure license is lowercase
        output["license"] = output["license"].lower()

        # Ensure URLs have scheme
        url_fields = ["url", "creator_url", "foreign_landing_url"]
        for url_field in url_fields:
            output[url_field] = add_protocol(output[url_field])

        return output

    def build_property_field(self, field_name, model_class):
        """
        Overrides the built-in property field builder to use docstrings as the Swagger
        help text for fields.

        :param field_name: the name of the property for which the field is being built
        :param model_class: the ``class`` instance for the Django model
        :return: the Field subclass to use and the keyword arguments to pass to it
        """

        klass, kwargs = super().build_property_field(field_name, model_class)
        if doc := getattr(model_class, field_name).__doc__:
            kwargs.setdefault("help_text", doc)
        return klass, kwargs


def get_hyperlinks_serializer(media_type):
    class MediaHyperlinksSerializer(serializers.Serializer):
        """
        This serializer creates URLs pointing to other endpoints related with this media
        item such as details and related media.
        """

        field_names = [
            "thumbnail",  # Not suffixed with `_url` because it points to an image
            "detail_url",
            "related_url",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

        thumbnail = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-thumb",
            lookup_field="identifier",
            help_text="A direct link to the miniature artwork.",
        )
        detail_url = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-detail",
            lookup_field="identifier",
            help_text="A direct link to the detail view of this audio file.",
        )
        related_url = SchemableHyperlinkedIdentityField(
            read_only=True,
            view_name=f"{media_type}-related",
            lookup_field="identifier",
            help_text="A link to an endpoint that provides similar audio files.",
        )

    return MediaHyperlinksSerializer
