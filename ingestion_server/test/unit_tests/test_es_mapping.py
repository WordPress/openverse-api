import pytest

from ingestion_server.es_mapping import index_settings


@pytest.mark.parametrize(
    "media_types, field_name, contents",
    [
        # common mappings
        (["audio", "image"], "authority_boost", {"type": "rank_feature"}),
        (
            ["audio", "image"],
            "authority_penalty",
            {"type": "rank_feature", "positive_score_impact": False},
        ),
        (["audio", "image"], "category", {"type": "keyword"}),
        (["audio", "image"], "created_on", {"type": "date"}),
        (["audio", "image"], "mature", {"type": "boolean"}),
        # image-specific mappings
        (["image"], "aspect_ratio", {"type": "keyword"}),
        # audio-specific mappings
        (["audio"], "genres", {"type": "keyword"}),
    ],
)
def test_mappings(media_types: list[str], field_name: str, contents: dict):
    for media_type in media_types:
        mapping = index_settings(media_type)
        assert mapping["mappings"]["properties"][field_name] == contents
