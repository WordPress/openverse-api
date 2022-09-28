#!/usr/bin/env python3
import json
import subprocess
from dataclasses import dataclass


@dataclass
class Service:
    name: str
    bindings: list[tuple[str, int, int]]

    def print(self):
        """
        Print the formatted output for the service. The output contains the following:
        - name (in bold)
        - each URL (with the correct protocol) and the container port to which it maps

        It specially handles the singular NGINX port 9443 which serves over ``https``.
        """

        print(f"\033[1m{self.name}:\033[0m")
        for url, host_port, container_port in self.bindings:
            proto = "http"
            if self.name == "proxy" and container_port == 9443:
                proto = "https"
            print(f"- {proto}://{url}:{host_port} (→ {container_port})")


def get_ps() -> str:
    """
    Invoke Docker Compose to get the current status of all services. This function uses
    the ``format`` flag to get the output as JSON which can be parsed and wrangled.

    :return: the output printed by the subprocess to STDOUT
    """

    proc = subprocess.run(
        ["just", "dc", "ps", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def parse_ps() -> list[Service]:
    """
    Convert the JSON output given by Docker Compose into a list of services and their
    port mappings.

    :return: a list of running services with their port
    """

    services: list[Service] = []

    data = json.loads(get_ps())
    for service in data:
        name = service["Service"]

        bindings = []
        publishers = service["Publishers"]
        for publisher in publishers:
            url = publisher["URL"]
            container_port = publisher["TargetPort"]
            host_port = publisher["PublishedPort"]
            if host_port:
                bindings.append((url, host_port, container_port))
        if bindings:
            services.append(Service(name, bindings))

    return services


def print_ps():
    """Print the formatted output for each service."""

    for service in parse_ps():
        service.print()


if __name__ == "__main__":
    print_ps()
