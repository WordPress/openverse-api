from __future__ import annotations

from elasticsearch_dsl import Range


AUDIO_CATEGORIES = {
    "audiobook",
    "music",
    "news",
    "podcast",
    "pronunciation",
    "sound_effect",
}

IMAGE_CATEGORIES = {
    "digitized_artwork",
    "illustration",
    "photograph",
}

ASPECT_RATIOS = {
    "tall",
    "wide",
    "square",
}

IMAGE_SIZES = {
    "small",
    "medium",
    "large",
}

RANGES = {
    "duration": {
        "short": Range(lte=4 * 60 * 1e3),
        "medium": Range(gt=4 * 60 * 1e3, lte=20 * 60 * 1e3),
        "long": Range(gt=20 * 60 * 1e3),
    }
}
