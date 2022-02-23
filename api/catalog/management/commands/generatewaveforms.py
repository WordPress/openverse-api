import logging
import subprocess

from catalog.api.models.audio import Audio
from django_tqdm import BaseCommand


class Command(BaseCommand):
    help = "Generates waveforms for all audio records to populate the cache"

    def handle(self, *args, **options):
        # These logs really muck up the tqdm output and don't give us much helpful
        # information, so they get silenced
        logging.getLogger("catalog.api.utils.waveform").setLevel(logging.WARNING)

        audios = Audio.objects.all().order_by("id")
        count = audios.count()
        self.stdout.write(
            self.style.NOTICE(f"Generating waveforms for {count:,} records")
        )
        with self.tqdm(total=count) as progress:
            for audio in audios:
                try:
                    audio.get_or_create_waveform()
                except subprocess.CalledProcessError as err:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Unable to process {audio.identifier}: "
                            f"{err.stderr.decode().strip()}"
                        )
                    )
                progress.update(1)

        self.stdout.write(self.style.SUCCESS("Finished generating waveforms!"))
