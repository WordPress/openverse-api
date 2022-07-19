from django.core.management import call_command, BaseCommand
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename
from pathlib import Path
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        file_path = str((Path(__file__).parent / "openapi.yaml").absolute())
        call_command('generateschema', file=file_path)
        spec_dict, spec_url = read_from_filename(file_path)
        try:
            validate_spec(spec_dict)
        finally:
            os.remove(file_path)
