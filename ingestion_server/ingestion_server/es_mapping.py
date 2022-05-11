import json
from pathlib import Path


def _get_json_file(json_path: Path) -> dict:
    """
    Read and parse the JSON file at the given path.

    :param json_path: the path to the JSON file to be read
    :return: the parsed contents of the JSON file
    """

    with json_path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def _get_mapping(name: str = "common") -> dict:
    """
    Get the field mappings for the ES index from the given JSON file. The name of the
    JSON file is ideally the same as the table or index name.

    :param name: the name of the JSON file to read, preferably named after the index
    :return: the parsed contents of the JSON file
    """

    json_path = Path(__file__).parent / "indices" / "mappings" / f"{name}.json"
    return _get_json_file(json_path)


def _get_settings() -> dict:
    """
    Get the settings from the ``settings.json`` file combined with some index specific
    settings such as number of shards and replicas, and refresh interval.

    :return: the settings for the ES mapping
    """

    json_path = Path(__file__).parent / "indices" / "settings.json"
    return _get_json_file(json_path) | {
        "index": {
            "number_of_shards": 18,
            "number_of_replicas": 0,
            "refresh_interval": "-1",
        },
    }


settings = _get_settings()
common_properties = _get_mapping()


def index_settings(table_name: str) -> dict:
    """
    Return the Elasticsearch mapping for a given table in the database.

    :param table_name: The name of the table in the upstream database.
    :return: the dictionary of settings to use when creating the index
    """

    mappings = {
        "dynamic": False,  # extra fields are stored in ``_source`` but not indexed
        "properties": common_properties | _get_mapping(table_name),
    }
    result = {"settings": settings, "mappings": mappings}
    return result
