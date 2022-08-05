"""
Also see `ingestion_server/constants/media_types.py`
"""

from typing import Literal, get_args


AUDIO_TYPE = "audio"
IMAGE_TYPE = "image"
MODEL_3D_TYPE = "model_3d"

MediaType = Literal[AUDIO_TYPE, IMAGE_TYPE, MODEL_3D_TYPE]

MEDIA_TYPES: list[MediaType] = list(get_args(MediaType))

MEDIA_TYPE_CHOICES = [(AUDIO_TYPE, "Audio"), (IMAGE_TYPE, "Image")]
