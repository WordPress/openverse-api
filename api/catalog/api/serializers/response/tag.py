from rest_framework import serializers


class TagSerializer(serializers.Serializer):
    """
    This output serializer serializes a singular tag.
    """

    name = serializers.CharField(
        required=True,
        help_text="The name of a detailed tag.",
    )
    accuracy = serializers.FloatField(
        required=False,
        help_text="The accuracy of a machine-generated tag. Human-generated "
        "tags do not have an accuracy field.",
    )
