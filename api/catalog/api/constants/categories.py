from django.db import models


class AudioCategories(models.TextChoices):
    AUDIOBOOK = "audiobook", "Audiobooks"
    MUSIC = "music", "Music"
    NEWS = "news", "News"
    PODCAST = "podcast", "Podcasts"
    PRONUNCIATION = "pronunciation", "Pronunciations"
    SOUND_EFFECT = "sound_effect", "Sound Effects"


class ImageCategories(models.TextChoices):
    DIGITIZED_ARTWORK = "digitized_artwork", "Digitized Artworks"
    ILLUSTRATION = "illustration", "Illustrations"
    PHOTOGRAPH = "photograph", "Photographs"
