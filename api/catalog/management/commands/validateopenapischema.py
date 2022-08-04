from django.core.management import call_command, BaseCommand
from openapi_spec_validator import validate_v2_spec
from openapi_spec_validator.readers import read_from_filename
from pathlib import Path
import os
from tempfile import gettempdir
from argparse import ArgumentParser

class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--output-dir",
            default=Path(".").absolute(),
            help="The direction into which to output the spec file. Defaults the the current working directory."
        )

    def handle_validation(self, spec_dict: dict):
        """
        This method should raise an error if the spec is not valid.
        """
        validate_v2_spec(spec_dict)

        invalid_paths = [p for p in spec_dict["paths"].keys() if not p.endswith('/')]

        assert invalid_paths == [], (
            "All paths must end with a trailing slash. "
            f"Found {len(invalid_paths)} missing a trailing "
            f"slash: {', '.join(invalid_paths)}"
        )

    def handle(self, *args, **options):
        file_path = str((Path(options["output_dir"]).absolute() / "openapi.yaml").absolute())
        call_command("generate_swagger", file_path, overwrite=True)
        spec_dict, spec_url = read_from_filename(file_path)
        self.handle_validation(spec_dict)
        os.remove(file_path)
