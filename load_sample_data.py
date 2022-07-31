#!/usr/bin/env python
import json
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Literal

from decouple import config
from python_on_whales import docker


WEB_SERVICE_NAME = config("WEB_SERVICE_NAME", default="web")
CACHE_SERVICE_NAME = config("CACHE_SERVICE_NAME", default="cache")
UPSTREAM_DB_SERVICE_NAME = config("UPSTREAM_DB_SERVICE_NAME", default="upstream_db")
DB_SERVICE_NAME = config("DB_SERVICE_NAME", default="db")

MEDIA_TYPES = ["image", "audio"]
MediaType = Literal["image", "audio"]


##########
# Models #
##########


@dataclass
class Provider:
    identifier: str
    name: str
    url: str
    media_type: str
    filter_content: bool = False

    @property
    def sql_value(self) -> str:
        fields = ", ".join(
            [
                "now()",
                f"'{self.identifier}'",
                f"'{self.name}'",
                f"'{self.url}'",
                f"'{self.media_type}'",
                str(self.filter_content).lower(),
            ]
        )
        return f"({fields})"


@dataclass
class Column:
    name: str
    type: str


###########
# Helpers #
###########


def compose_exec(service: str, bash_input: str) -> str:
    """
    Run the given input inside a Bash shell inside the container.

    :param service: the name of the service inside which to execute the commands
    :param bash_input: the input for the Bash shell
    :return: the output of the operation
    """

    bash_input = re.sub(r"\n\s{8}", r"\n", bash_input)
    return docker.compose.execute(service, ["/bin/bash", "-c", bash_input], tty=False)


def copy_table_upstream(
    name: str, target_name: str = None, delete_if_exists: bool = True
):
    """
    Copy the given table from the downstream DB to the upstream DB. Any existing table
    with the same name can be deleted before copying and the table can be renamed after
    copying.

    :param name: the name of the source table to copy
    :param target_name: the name to assign to the copied table
    :param delete_if_exists: whether to delete any existing tables with the target name
    """

    if target_name is None:
        target_name = name

    bash_input = (
        "PGPASSWORD=deploy "
        f"pg_dump -s -t {name} -U deploy -d openledger -h {DB_SERVICE_NAME} | "
        "psql -U deploy -d openledger"
    )

    if delete_if_exists:
        # Delete existing table before copying.
        bash_input = f"""psql -U deploy -d openledger <<EOF
DROP TABLE IF EXISTS {target_name} CASCADE;
EOF
{bash_input}"""

    if target_name != name:
        # Rename table after copying.
        bash_input = f"""{bash_input}
psql -U deploy -d openledger <<EOF
ALTER TABLE {name}
    RENAME TO {target_name};
EOF"""
    print(compose_exec(UPSTREAM_DB_SERVICE_NAME, bash_input))


def run_just(recipe: str, argv: list[str]) -> subprocess.CompletedProcess:
    """
    Run the given ``just`` recipe with the given arguments.

    :param recipe: the name of the ``just`` recipe to invoke
    :param argv: the list of arguments to pass after the ``just`` recipe
    :return: the process obtained from the ``subprocess.run`` command
    """

    try:
        proc = subprocess.run(
            ["just", recipe, *argv],
            check=True,
            capture_output=True,
            text=True,
        )
        print(proc.stdout)
        return proc
    except subprocess.CalledProcessError as exc:
        print(exc.stdout)
        print(exc.stderr, file=sys.stderr)
        raise


#########
# Steps #
#########


def run_migrations():
    """
    Run all migrations for the API.
    """

    bash_input = "python manage.py migrate --noinput"
    print(compose_exec(WEB_SERVICE_NAME, bash_input))


def create_users(names: list[str]):
    """
    Create users with the given usernames in the API database. The password for the
    users is always set to "deploy". Users that already exist will not be recreated.
    """

    bash_input = f"""python manage.py shell <<EOF
        from django.contrib.auth.models import User
        usernames = {names}
        for username in usernames:
            if User.objects.filter(username=username).exists():
                print(f'User {{username}} already exists')
                continue
            if username == 'deploy':
                user = User.objects.create_superuser(
                    username, f'{{username}}@example.com', 'deploy'
                )
            else:
                user = User.objects.create_user(
                    username, f'{{username}}@example.com', 'deploy'
                )
                user.save()
        EOF"""
    print(compose_exec(WEB_SERVICE_NAME, bash_input))


def backup_table(media_type: MediaType):
    """
    Create a backup of the table created for the given media type. This table will be
    free of the modifications made during ingestion and thereby allow making the ingest
    step idempotent.

    :param media_type: the media type whose table is being backed up
    """

    bash_input = f"""psql -U deploy -d openledger <<EOF
        CREATE TABLE {media_type}_template
            (LIKE {media_type} INCLUDING ALL);
        CREATE SEQUENCE {media_type}_template_id_seq;
        ALTER TABLE {media_type}_template
            ALTER COLUMN id
            SET DEFAULT nextval('{media_type}_template_id_seq');
        ALTER SEQUENCE {media_type}_template_id_seq
            OWNED BY {media_type}_template.id;
        EOF"""
    print(compose_exec(DB_SERVICE_NAME, bash_input))


def load_content_providers(providers: list[Provider]):
    """
    Load the given providers into the database. The given providers will be removed from
    the database, if they exist, and then re-added.

    :param providers: the list of providers to load
    """

    identifiers = ", ".join([f"'{provider.identifier}'" for provider in providers])
    values = ", ".join([provider.sql_value for provider in providers])

    bash_input = f"""psql -U deploy -d openledger <<EOF
        DELETE FROM content_provider
            WHERE provider_identifier IN ({identifiers});
        INSERT INTO content_provider
            (created_on,provider_identifier,provider_name,domain_name,media_type,filter_content)
        VALUES
            {values};
        EOF"""
    print(compose_exec(DB_SERVICE_NAME, bash_input))


def load_sample_data(media_type: MediaType, extra_columns: list[Column] = None):
    """
    Copy data from the sample data files into the upstream DB tables. Any extra columns
    required can be added to the table.

    :param media_type: the name of the model to copy sample data for
    :param extra_columns: the list of additional columns to create on the table
    """

    source_table = f"{media_type}_template"
    dest_table = f"{media_type}_view"
    copy_table_upstream(source_table, dest_table)

    add = ""
    if extra_columns:
        add_directives = ", ".join(
            [f"ADD COLUMN {column.name} {column.type}" for column in extra_columns]
        )
        add = f"ALTER TABLE {dest_table} {add_directives};\n"

    sample_file_path = f"./sample_data/sample_{media_type}.csv"
    with open(sample_file_path, "r") as sample_file:
        columns = sample_file.readline().strip()
    copy = (
        f"\\copy {dest_table} ({columns}) from '{sample_file_path}' "
        "with (FORMAT csv, HEADER true);\n"
    )

    bash_input = f"""psql -U deploy -d openledger <<EOF
        {add}
        {copy}
        EOF"""
    print(compose_exec(UPSTREAM_DB_SERVICE_NAME, bash_input))


def create_audioset_view():
    """
    Create the ``audioset_view`` view from the ``audio_view`` table by breaking the
    ``audio_set`` JSONB field into its constituent keys as separate columns.
    """

    columns = [
        Column("foreign_identifier", "varchar(1000)"),
        Column("title", "varchar(2000)"),
        Column("foreign_landing_url", "varchar(1000)"),
        Column("creator", "varchar(2000)"),
        Column("creator_url", "varchar(2000)"),
        Column("url", "varchar(1000)"),
        Column("filesize", "integer"),
        Column("filetype", "varchar(80)"),
        Column("thumbnail", "varchar(1000)"),
    ]
    select_directives = ", ".join(
        [
            f"(audio_set ->> '{column.name}') :: {column.type} as {column.name}"
            for column in columns
        ]
    )

    bash_input = f"""psql -U deploy -d openledger <<EOF
        UPDATE audio_view
            SET audio_set_foreign_identifier = audio_set ->> 'foreign_identifier';
        DROP VIEW IF EXISTS audioset_view;
        CREATE VIEW audioset_view
        AS
            SELECT DISTINCT
                {select_directives},
                provider
            FROM audio_view
            WHERE audio_set IS NOT NULL;
        EOF"""
    print(compose_exec(UPSTREAM_DB_SERVICE_NAME, bash_input))


def ingest(media_type: MediaType):
    """
    Create test data and actual indices for the given media type. New indices are
    created in each run so repeatedly running may fill up ES to maximum capacity.

    :param media_type: the media type for which to create ES indices
    """

    run_just("load-test-data", [media_type])
    time.sleep(2)  # seconds

    proc = run_just("stat", [media_type])
    data = json.loads(proc.stdout)

    suffix = uuid.uuid4().hex

    # TODO: Find the cause of flaky image ingestion.
    retries = 2 if media_type == "image" else 0
    while True:
        try:
            run_just("ingest-upstream", [media_type, suffix])
            run_just("wait-for-index", [f"{media_type}-{suffix}"])
            break
        except subprocess.CalledProcessError:
            if not retries:
                raise
            print("Retrying due to failure")
            retries -= 1

    run_just("promote", [media_type, suffix, media_type])
    run_just("wait-for-index", [media_type])

    if data["exists"]:
        old_suffix = data["alt_names"].lstrip(f"{media_type}-")
        run_just("delete-index", [media_type, old_suffix])


if __name__ == "__main__":
    # API initialisation
    run_migrations()
    create_users(["deploy", "continuous_integration"])
    for media_type in MEDIA_TYPES:
        backup_table(media_type)

    providers = [
        Provider("flickr", "Flickr", "https://www.flickr.com", "image"),
        Provider("stocksnap", "StockSnap", "https://stocksnap.io", "image"),
        Provider("freesound", "Freesound", "https://freesound.org/", "audio"),
        Provider("jamendo", "Jamendo", "https://www.jamendo.com", "audio"),
        Provider(
            "wikimedia_audio", "Wikimedia", "https://commons.wikimedia.org", "audio"
        ),
    ]
    load_content_providers(providers)

    # Upstream initialisation
    copy_table_upstream("content_provider")

    standardized_popularity = Column("standardized_popularity", "double precision")
    ingestion_type = Column("ingestion_type", "varchar(1000)")
    audio_set = Column("audio_set", "jsonb")
    extra_columns = {
        "image": [standardized_popularity, ingestion_type],
        "audio": [standardized_popularity, ingestion_type, audio_set],
    }
    for media_type in MEDIA_TYPES:
        load_sample_data(media_type, extra_columns[media_type])

    create_audioset_view()

    # Data refresh
    for media_type in MEDIA_TYPES:
        ingest(media_type)

    # Cache bust
    for media_type in MEDIA_TYPES:
        compose_exec(
            CACHE_SERVICE_NAME, f'echo "del :1:sources-{media_type}" | redis-cli'
        )
