from rest_framework import serializers
# image serializer category
imageCategories = serializers.CharField(
        label="categories",
        help_text="A comma separated list of categories; available categories "
        "include `illustration`, `photograph`, and "
        "`digitized_artwork`.",
        required=False,
    )

# audio serializer category 
audioCategories = serializers.CharField(
        label="categories",
        help_text="A comma separated list of categories; available categories "
        "include `music`, `sound_effect`, `podcast`, `audiobook`, "
        "and `news`.",
        required=False,
    )