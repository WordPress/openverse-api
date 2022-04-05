class Categories(set):
    def make_help_text(self) -> str:
        """
        Generate help text that wraps each category in backticks.
        """
        formatted = [f"`{category}`" for category in self]
        # Add an "and" at the end of the list
        if len(formatted) > 1:
            formatted[-1] = f"and {formatted[-1]}"
        help_text = (
            "A comma separated list of categories; available categories include: "
            f"{', '.join(formatted)}."
        )
        return help_text


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
