"""
Parses the top-level Docker Compose file and generates one for the integration tests.

The generated file is written to the same directory this script resides in with
the name ``integration-docker-compose.yml``.

A new file is generated instead of inheritance because using an inherited file
will result in the containers being destroyed and recreated. By using generated
files we ensure an up-to-date copy that does not interfere with the development
environment.
"""

import pathlib

import yaml

from .test_constants import service_ports


this_dir = pathlib.Path(__file__).resolve().parent

# Docker Compose config will be copied from ``src_dc_path`` to ``dest_dc_path``
src_dc_path = this_dir.parent.parent.joinpath("docker-compose.yml")
dest_dc_path = this_dir.joinpath("integration-docker-compose.yml")


def _prune_services(conf: dict):
    """
    Prune the unnecessary services from the Docker Compose configuration.

    After this step, only those that are used in the integration tests are left.

    :param conf: the Docker Compose configuration
    """

    services_to_keep = {"es", "ingestion_server", "indexer_worker", "db", "upstream_db"}
    for service_name in dict(conf["services"]):
        if service_name not in services_to_keep:
            del conf["services"][service_name]


def _map_ports(conf: dict):
    """
    Change the port mappings for the services to avoid conflicts.

    This ensures that the test containers do not use the same ports as dev containers
    that might already be using them.

    :param conf: the Docker Compose configuration
    """

    for service_name, service in conf["services"].items():
        if "ports" in service:
            ports = service["ports"]
            ports = [
                f"{service_ports[service_name]}:{port.split(':')[1]}" for port in ports
            ]
            service["ports"] = ports
        elif "expose" in service and service_name in service_ports:
            exposes = service["expose"]
            ports = [f"{service_ports[service_name]}:{expose}" for expose in exposes]
            service["ports"] = ports


def _fixup_env(conf: dict):
    """
    Change the relative paths to the environment files to absolute paths.

    This ensures that they are point to valid locations in the new Docker Compose file.

    :param conf: the Docker Compose configuration
    """

    for service in {"db", "upstream_db"}:
        env_files = conf["services"][service]["env_file"]
        env_files = [str(src_dc_path.parent.joinpath(path)) for path in env_files]
        conf["services"][service]["env_file"] = env_files
    for service in {"ingestion_server", "indexer_worker"}:
        conf["services"][service]["env_file"] = ["env.integration"]


def _remove_volumes(conf: dict):
    """
    Remove the volumes from the compose configuration.

    This ensures that the images begin with a fresh start on every startup.

    :param conf: the Docker Compose configuration
    """
    volumes_to_remove = {
        "db": "api-postgres",
        "upstream_db": "catalog-postgres",
        "es": "es-data",
    }

    for service, volume_to_remove in volumes_to_remove.items():
        volumes = conf["services"][service]["volumes"]
        volumes = [volume for volume in volumes if volume_to_remove not in volume]
        conf["services"][service]["volumes"] = volumes

    conf["volumes"] = {}


def _change_directories(conf: dict):
    """
    Update the relative paths of the directories like build context or bind volumes.

    :param conf: the Docker Compose configuration
    """

    for service in {"ingestion_server", "indexer_worker"}:
        conf["services"][service]["volumes"] = ["../:/ingestion_server"]
        conf["services"][service]["build"] = "../"

    conf["services"]["upstream_db"]["volumes"] = ["./mock_data:/mock_data"]


def _rename_services(conf: dict):
    """
    Add the 'integration_' prefix to the services to distinguish them from dev services.

    :param conf: the Docker Compose configuration
    """

    for service_name, service in dict(conf["services"]).items():
        conf["services"][f"integration_{service_name}"] = service
        del conf["services"][service_name]

    for service in {"ingestion_server", "indexer_worker"}:
        conf["services"][f"integration_{service}"]["depends_on"] = [
            "integration_db",
            "integration_es",
        ]


def gen_integration_compose():
    print("Generating Docker Compose configuration for integration tests...")

    with open(src_dc_path) as src_dc:
        conf = yaml.safe_load(src_dc)

        print("│ Pruning unwanted services... ", end="")
        _prune_services(conf)
        print("done")

        print("│ Mapping alternative ports... ", end="")
        _map_ports(conf)
        print("done")

        print("│ Updating environment variables... ", end="")
        _fixup_env(conf)
        print("done")

        print("│ Removing volumes... ", end="")
        _remove_volumes(conf)
        print("done")

        print("│ Changing directories... ", end="")
        _change_directories(conf)
        print("done")

        print("│ Renaming services... ", end="")
        _rename_services(conf)
        print("done")

        with open(dest_dc_path, "w") as dest_dc:
            dest_dc.write(
                "# This is an auto-generated Docker Compose configuration file.\n"
                "# Do not modify this file directly. Your changes will be overwritten.\n\n"
            )
            yaml.dump(conf, dest_dc, default_flow_style=False)

    print("done\n")
    return dest_dc_path


if __name__ == "__main__":
    dest_path = gen_integration_compose()

    green = "\033[32m"
    endcol = "\033[0m"
    print(f"{green}:-) Docker Compose configuration written to {dest_path}{endcol}")
