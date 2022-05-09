from typing import Any, Optional


def _text_keyword(ignore_above: Optional[int] = 256) -> dict:
    """
    Return the schema for a ``text`` field that must be broken down into ``keyword``
    fields.

    :param ignore_above: the limit above which text will not be stored or indexed
    :return: the schema for a text field to break into keywords
    """

    keyword_field = {"type": "keyword"}
    if ignore_above is not None:
        keyword_field["ignore_above"] = ignore_above
    return {"fields": {"keyword": keyword_field}, "type": "text"}


def index_settings(table_name):
    """
    Return the Elasticsearch mapping for a given table in the database.

    :param table_name: The name of the table in the upstream database.
    :return: the dictionary of settings to use when creating the index
    """

    settings = {
        "index": {
            "number_of_shards": 18,
            "number_of_replicas": 0,
            "refresh_interval": "-1",
        },
        "analysis": {
            "filter": {
                "stem_overrides": {
                    "type": "stemmer_override",
                    "rules": [
                        # Override unwanted 'anim' stems
                        "animals => animal",
                        "animal => animal",
                        "anime => anime",
                        "animate => animate",
                        "animated => animate",
                    ],
                },
                "english_stop": {"type": "stop", "stopwords": "_english_"},
                "english_stemmer": {"type": "stemmer", "language": "english"},
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english",
                },
            },
            "analyzer": {
                "custom_english": {
                    "tokenizer": "standard",
                    "filter": [
                        # Stem overrides must appear before the primary
                        # language stemmer.
                        "stem_overrides",
                        "english_possessive_stemmer",
                        "lowercase",
                        "english_stop",
                        "english_stemmer",
                    ],
                }
            },
        },
    }

    common_properties: dict[str, Any] = {
        "id": {"type": "long"},
        "title": _text_keyword()
        | {
            "similarity": "boolean",
            "analyzer": "custom_english",
        },
        "description": _text_keyword()
        | {
            "similarity": "boolean",
            "analyzer": "custom_english",
        },
        "created_on": {"type": "date"},
        "tags": {
            "properties": {
                "accuracy": {"type": "float"},
                "name": _text_keyword()
                | {
                    "analyzer": "custom_english",
                },
            }
        },
        "mature": {"type": "boolean"},
        "category": {"type": "keyword"},
    }

    text_keywords = [
        "identifier",
        "creator",
        ("extension", 8),
        "license",
        "license_version",
        "provider",
        "source",
    ]
    for text_keyword in text_keywords:
        if isinstance(text_keyword, tuple):
            text_keyword, ignore_above = text_keyword
            field = _text_keyword(ignore_above)
        else:
            field = _text_keyword()
        common_properties[text_keyword] = field

    # Configure positive and negative rank features
    rank_features = [
        "standardized_popularity",
        "min_boost",
        "max_boost",
        "authority_boost",
        ("authority_penalty", False),
    ]
    for rank_feature in rank_features:
        positive_score_impact = True
        if isinstance(rank_feature, tuple):
            rank_feature, positive_score_impact = rank_feature
        field = {"type": "rank_feature", "positive_score_impact": positive_score_impact}
        common_properties[rank_feature] = field

    media_properties = {
        "image": {
            field: _text_keyword() for field in ["thumbnail", "aspect_ratio", "size"]
        },
        "audio": {"genres": _text_keyword()}
        | {
            field: {"type": "integer"}
            for field in ["bit_rate", "sample_rate", "duration"]
        },
    }

    media_mappings = {
        "dynamic": False,  # extra fields are stored in ``_source`` but not indexed
        "properties": common_properties | media_properties[table_name],
    }
    result = {"settings": settings.copy(), "mappings": media_mappings}
    return result
