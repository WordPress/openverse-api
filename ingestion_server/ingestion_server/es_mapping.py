def index_settings(table_name):
    """
    Return the Elasticsearch mapping for a given table in the database.

    :param table_name: The name of the table in the upstream database.
    :return:
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
    common_mappings = {
        "properties": {
            "id": {"type": "long"},
            "identifier": {
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                "type": "text",
            },
            "title": {
                "type": "text",
                "similarity": "boolean",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                "analyzer": "custom_english",
            },
            "foreign_landing_url": {
                "fields": {"keyword": {"ignore_above": 256, "type": "keyword"}},
                "type": "text",
            },
            "description": {
                "fields": {"keyword": {"type": "keyword", "similarity": "boolean"}},
                "type": "text",
                "analyzer": "custom_english",
            },
            "creator": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "url": {
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                "type": "text",
            },
            "extension": {
                "fields": {"keyword": {"ignore_above": 8, "type": "keyword"}},
                "type": "text",
            },
            "license": {
                "fields": {"keyword": {"ignore_above": 256, "type": "keyword"}},
                "type": "text",
            },
            "license_version": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "license_url": {
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                "type": "text",
            },
            "provider": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "source": {
                "fields": {"keyword": {"ignore_above": 256, "type": "keyword"}},
                "type": "text",
            },
            "created_on": {"type": "date"},
            "tags": {
                "properties": {
                    "accuracy": {"type": "float"},
                    "name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                        "analyzer": "custom_english",
                    },
                }
            },
            "mature": {"type": "boolean"},
            "standardized_popularity": {"type": "rank_feature"},
            "authority_boost": {"type": "rank_feature"},
            "authority_penalty": {
                "type": "rank_feature",
                "positive_score_impact": False,
            },
            "max_boost": {"type": "rank_feature"},
            "min_boost": {"type": "rank_feature"},
        }
    }
    media_properties = {
        "image": {
            "aspect_ratio": {
                "fields": {"keyword": {"type": "keyword"}},
                "type": "text",
            },
            "size": {"fields": {"keyword": {"type": "keyword"}}, "type": "text"},
        },
        "audio": {
            "bit_rate": {"type": "integer"},
            "sample_rate": {"type": "integer"},
            "genres": {"fields": {"keyword": {"type": "keyword"}}, "type": "text"},
            "duration": {"type": "integer"},
            "category": {"type": "text"},
        },
    }
    media_mappings = common_mappings.copy()
    media_mappings["properties"].update(media_properties[table_name])
    result = {"settings": settings.copy(), "mappings": media_mappings}
    return result
