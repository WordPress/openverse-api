from django.core.management import call_command, BaseCommand
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename
from pathlib import Path
import os

class Command(BaseCommand):
    def handle_validation(self, spec_dict: dict):
        """
        This method should raise an error if the spec is not valid.
        """
        validate_spec(spec_dict)

        invalid_paths = [p for p in spec_dict["paths"].keys() if not p.endswith('/')]

        assert invalid_paths == [], (
            "All paths must end with a trailing slash. "
            f"Found {len(invalid_paths)} missing a trailing "
            f"slash: {', '.join(invalid_paths)}"
        )


    def handle(self, *args, **kwargs):
        file_path = str((Path(__file__).parent / "openapi.yaml").absolute())
        call_command('generateschema', file=file_path)
        spec_dict, spec_url = read_from_filename(file_path)
        try:
            self.handle_validation(spec_dict)
        finally:
            os.remove(file_path)
