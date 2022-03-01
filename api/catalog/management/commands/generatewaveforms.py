import logging
import subprocess

from catalog.api.models.audio import Audio, AudioAddOn
from django_tqdm import BaseCommand


def paginate_reducing_query(get_query_set, page_size=10):
    """
    We can't use `Paginator` because it can't handle the situation
    where the query result changes each time a page is accessed.
    Because the `audios` QuerySet result is naturally getting smaller
    each time we successfully process waveforms, we can just take
    the first ten for each "page" until the page comes back empty.
    This should theoretically be faster/less DB latency inducing
    anyway as we're never going to have huge OFFSET values to
    access deep pages.
    """
    page = list(get_query_set()[0:page_size])
    while len(page):
        yield page
        page = list(get_query_set()[0:page_size])


class Command(BaseCommand):
    help = "Generates waveforms for all audio records to populate the cache."
    """
    Note: We rely on the file download and waveform generation times
    taking long enough to prevent us from either making too many requests
    to the upstream provider or inserting into our database too quickly and
    causing a slow down. In local tests and in tests run on the staging server
    it appeared to take on average around 6 to 8 seconds for each audio file.
    That should be enough latency to not cause any problems.
    """

    def handle(self, *args, **options):
        # These logs really muck up the tqdm output and don't give us much helpful
        # information, so they get silenced
        logging.getLogger("catalog.api.utils.waveform").setLevel(logging.WARNING)

        existing_waveform_audio_identifiers_query = AudioAddOn.objects.filter(
            waveform_peaks__isnull=False
        ).values_list("audio_identifier", flat=True)
        audios = Audio.objects.exclude(
            identifier__in=existing_waveform_audio_identifiers_query
        ).order_by("id")
        count = audios.count()
        self.stdout.write(
            self.style.NOTICE(f"Generating waveforms for {count:,} records")
        )
        errored_identifiers = []
        with self.tqdm(total=count) as progress:
            paginator = paginate_reducing_query(
                get_query_set=lambda: audios.exclude(identifier__in=errored_identifiers)
            )
            for page in paginator:
                for audio in page:
                    try:
                        audio.get_or_create_waveform()
                    except subprocess.CalledProcessError as err:
                        errored_identifiers.append(audio.identifier)
                        self.stderr.write(
                            self.style.ERROR(
                                f"Unable to process {audio.identifier}: "
                                f"{err.stderr.decode().strip()}"
                            )
                        )
                    except BaseException as err:
                        errored_identifiers.append(audio.identifier)
                        self.stderr.write(
                            self.style.ERROR(
                                f"Unable to process {audio.identifier}: " f"{err}"
                            )
                        )
                    progress.update(1)

        self.stdout.write(self.style.SUCCESS("Finished generating waveforms!"))
