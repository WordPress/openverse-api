from pathlib import Path
from typing import Literal, Union

import yaml

from ingestion_server.constants.media_types import MediaType


def _get_yaml_data(yaml_path: Path) -> dict:
    """
    Read and parse the YAML file at the given path.

    :param yaml_path: the path pointing to the YAML file to parse
    :return: the parsed contents of the YAML file
    """

    with yaml_path.open("r") as yaml_file:
        return yaml.safe_load(yaml_file)


def _get_mapping(name: Union[Literal["common"], MediaType] = "common") -> dict:
    """
    Get the field mappings for the ES index from the given JSON file. The name of the
    JSON file is ideally the same as the media type.

    :param name: the name of the JSON file to read, ideally named after the media type
    :return: the parsed contents of the JSON file
    """

    json_path = Path(__file__).parent / "indices" / "mappings" / f"{name}.yml"
    return _get_yaml_data(json_path)


def _get_settings() -> dict:
    """
    Get the settings from the ``settings.json`` file combined with some index specific
    settings such as number of shards and replicas, and refresh interval.
    :return: the settings for the ES mapping
    """

    json_path = Path(__file__).parent / "indices" / "settings.yml"
    index_settings = {
        "index": {
            "number_of_shards": 18,
            "number_of_replicas": 0,
            "refresh_interval": "-1",
        }
    }
    return _get_yaml_data(json_path) | index_settings


SETTINGS = _get_settings()
COMMON_PROPERTIES = _get_mapping()


def media_type_mapping(media_type: MediaType) -> dict:
    """
    Return the Elasticsearch mapping for a given media type.

    :param media_type: the name of the media type being indexed in ES
    :return: the dictionary of settings to use when creating the index
    """

    mappings = {
        "dynamic": False,  # extra fields are stored in ``_source`` but not indexed
        "properties": COMMON_PROPERTIES | _get_mapping(media_type),
    }
    result = {"settings": SETTINGS, "mappings": mappings}
    return result
