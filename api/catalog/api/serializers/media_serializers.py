from collections import namedtuple

from rest_framework import serializers

from catalog.api.constants.licenses import LICENSE_GROUPS
from catalog.api.controllers import search_controller
from catalog.api.models.media import AbstractMedia
from catalog.api.serializers.fields import SchemableHyperlinkedIdentityField
from catalog.api.utils.help_text import make_comma_separated_help_text
from catalog.api.utils.url import add_protocol


#######################
# Request serializers #
#######################


class MediaSearchRequestSerializer(serializers.Serializer):
    """
    This serializer parses and validates search query string parameters.
    """

    DeprecatedParam = namedtuple("DeprecatedParam", ["original", "successor"])
    deprecated_params = [
        DeprecatedParam("li", "license"),
        DeprecatedParam("lt", "license_type"),
        DeprecatedParam("pagesize", "page_size"),
        DeprecatedParam("provider", "source"),
    ]
    fields_names = [
        "q",
        "license",
        "license_type",
        "creator",
        "tags",
        "title",
        "filter_dead",
        "extension",
        "mature",
        "qa",
    ]
    """
    Keep the fields names in sync with the actual fields below as this list is
    used to generate Swagger documentation.
    """

    q = serializers.CharField(
        label="query",
        help_text="A query string that should not exceed 200 characters in length",
        required=False,
    )
    license = serializers.CharField(
        label="licenses",
        help_text=make_comma_separated_help_text(LICENSE_GROUPS["all"], "licenses"),
        required=False,
    )
    license_type = serializers.CharField(
        label="license type",
        help_text=make_comma_separated_help_text(
            LICENSE_GROUPS.keys(), "license types"
        ),
        required=False,
    )
    creator = serializers.CharField(
        label="creator",
        help_text="Search by creator only. Cannot be used with `q`.",
        required=False,
        max_length=200,
    )
    tags = serializers.CharField(
        label="tags",
        help_text="Search by tag only. Cannot be used with `q`.",
        required=False,
        max_length=200,
    )
    title = serializers.CharField(
        label="title",
        help_text="Search by title only. Cannot be used with `q`.",
        required=False,
        max_length=200,
    )
    filter_dead = serializers.BooleanField(
        label="filter_dead",
        help_text="Control whether 404 links are filtered out.",
        required=False,
        default=True,
    )
    extension = serializers.CharField(
        label="extension",
        help_text="A comma separated list of desired file extensions.",
        required=False,
    )
    mature = serializers.BooleanField(
        label="mature",
        default=False,
        required=False,
        help_text="Whether to include content for mature audiences.",
    )
    qa = serializers.BooleanField(
        label="quality_assurance",
        help_text="If enabled, searches are performed against the quality"
        " assurance index instead of production.",
        required=False,
        default=False,
    )

    @staticmethod
    def _truncate(value):
        max_length = 200
        return value if len(value) <= max_length else value[:max_length]

    def validate_q(self, value):
        return self._truncate(value)

    @staticmethod
    def validate_license(value):
        """Checks whether license is a valid license code."""

        licenses = value.lower().split(",")
        for _license in licenses:
            if _license not in LICENSE_GROUPS["all"]:
                raise serializers.ValidationError(
                    f"License '{_license}' does not exist."
                )
        return value.lower()

    @staticmethod
    def validate_license_type(value):
        """Checks whether license type is a known collection of licenses."""

        license_types = value.lower().split(",")
        license_groups = []
        for _type in license_types:
            if _type not in LICENSE_GROUPS:
                raise serializers.ValidationError(
                    f"License type '{_type}' does not exist."
                )
            license_groups.append(LICENSE_GROUPS[_type])
        intersected = set.intersection(*license_groups)
        return ",".join(intersected)

    def validate_creator(self, value):
        return self._truncate(value)

    def validate_tags(self, value):
        return self._truncate(value)

    def validate_title(self, value):
        return self._truncate(value)

    @staticmethod
    def validate_extension(value):
        return value.lower()

    def validate(self, data):
        data = super().validate(data)
        errors = {}
        for param, successor in self.deprecated_params:
            if param in self.initial_data:
                errors[param] = (
                    f"Parameter '{param}' is deprecated in this release of the API. "
                    f"Use '{successor}' instead."
                )
        if errors:
            raise serializers.ValidationError(errors)
        return data


class MediaThumbnailRequestSerializer(serializers.Serializer):
    """
    This serializer parses and validates thumbnail query string parameters.
    """

    full_size = serializers.BooleanField(
        source="is_full_size",
        allow_null=True,
        required=False,
        default=False,
        help_text="whether to render the actual image and not a thumbnail version",
    )
    compressed = serializers.BooleanField(
        source="is_compressed",
        allow_null=True,
        default=None,
        required=False,
        help_text="whether to compress the output image to reduce file size,"
        "defaults to opposite of `full_size`",
    )

    def validate(self, data):
        if data.get("is_compressed") is None:
            data["is_compressed"] = not data["is_full_size"]
        return data


########################
# Response serializers #
########################


class TagSerializer(serializers.Serializer):
    """
    This output serializer serializes a singular tag.
    """

    name = serializers.CharField(
        help_text="The name of a detailed tag.",
    )
    accuracy = serializers.FloatField(
        required=False,
        help_text="The accuracy of a machine-generated tag. Human-generated "
        "tags do not have an accuracy field.",
    )


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


#######################
# Dynamic serializers #
#######################


def get_search_request_source_serializer(media_type):
    class MediaSearchRequestSourceSerializer(serializers.Serializer):
        """
        This serializer parses and validates the source/not_source fields from the query
        parameters.
        """

        field_names = [
            "source",
            "excluded_source",
        ]
        """
        Keep the fields names in sync with the actual fields below as this list is
        used to generate Swagger documentation.
        """

        _field_attrs = {
            "help_text": make_comma_separated_help_text(
                search_controller.get_sources(media_type).keys(), "data sources"
            ),
            "required": False,
        }

        source = serializers.CharField(
            label="provider",
            **_field_attrs,
        )
        excluded_source = serializers.CharField(
            label="excluded_provider",
            **_field_attrs,
        )

        @staticmethod
        def validate_source_field(input_sources):
            allowed_sources = list(search_controller.get_sources(media_type).keys())
            input_sources = input_sources.split(",")
            input_sources = [x for x in input_sources if x in allowed_sources]
            input_sources = ",".join(input_sources)
            return input_sources.lower()

        def validate_source(self, input_sources):
            return self.validate_source_field(input_sources)

        def validate_excluded_source(self, input_sources):
            return self.validate_source(input_sources)

        def validate(self, data):
            data = super().validate(data)
            if "source" in self.initial_data and "excluded_source" in self.initial_data:
                raise serializers.ValidationError(
                    "Cannot set both 'source' and 'excluded_source'. "
                    "Use exactly one of these."
                )
            return data

    return MediaSearchRequestSourceSerializer


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
