from catalog.api.utils.help_text import CommaSeparatedField


class Categories(CommaSeparatedField):
    name = "categories"


AUDIO_CATEGORIES = Categories(
    [
        "audiobook",
        "music",
        "news",
        "podcast",
        "pronunciation",
        "sound_effect",
    ]
)


IMAGE_CATEGORIES = Categories(
    [
        "digitized_artwork",
        "illustration",
        "photograph",
    ]
)
