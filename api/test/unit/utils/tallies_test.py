from datetime import datetime

import pytest
from freezegun import freeze_time

from catalog.api.utils import tallies


@pytest.mark.parametrize(
    ("now", "expected_timestamp"),
    (
        pytest.param(datetime(2023, 1, 19), "2023-01-16", id="midweek"),
        pytest.param(datetime(2023, 1, 16), "2023-01-16", id="start_of_week"),
        pytest.param(datetime(2023, 1, 15), "2023-01-09", id="end_of_week"),
    ),
)
def test_count_provider_occurrences_uses_week_timestamp(now, expected_timestamp, redis):
    results = [{"provider": "flickr"} for _ in range(4)] + [
        {"provider": "stocksnap"} for _ in range(6)
    ]
    with freeze_time(now):
        tallies.count_provider_occurrences(results)

    assert redis.get(f"provider_occurrences:{expected_timestamp}:flickr") == b"4"
    assert redis.get(f"provider_occurrences:{expected_timestamp}:stocksnap") == b"6"
    assert (
        redis.get(f"provider_appeared_in_searches:{expected_timestamp}:flickr") == b"1"
    )
    assert (
        redis.get(f"provider_appeared_in_searches:{expected_timestamp}:stocksnap")
        == b"1"
    )


def test_count_provider_occurrences_increments_existing_tallies(redis):
    results_1 = [{"provider": "flickr"} for _ in range(4)] + [
        {"provider": "stocksnap"} for _ in range(6)
    ]

    results_2 = [{"provider": "flickr"} for _ in range(3)] + [
        {"provider": "inaturalist"} for _ in range(7)
    ]

    now = datetime(2023, 1, 19)  # 16th is start of week
    timestamp = "2023-01-16"
    with freeze_time(now):
        tallies.count_provider_occurrences(results_1)

    assert redis.get(f"provider_occurrences:{timestamp}:flickr") == b"4"
    assert redis.get(f"provider_occurrences:{timestamp}:stocksnap") == b"6"
    assert redis.get(f"provider_appeared_in_searches:{timestamp}:flickr") == b"1"
    assert redis.get(f"provider_appeared_in_searches:{timestamp}:stocksnap") == b"1"

    with freeze_time(now):
        tallies.count_provider_occurrences(results_2)

    assert redis.get(f"provider_occurrences:{timestamp}:flickr") == b"7"  # 4 + 7
    assert redis.get(f"provider_occurrences:{timestamp}:stocksnap") == b"6"  # no change
    assert redis.get(f"provider_occurrences:{timestamp}:inaturalist") == b"7"
    assert redis.get(f"provider_appeared_in_searches:{timestamp}:flickr") == b"2"
    assert redis.get(f"provider_appeared_in_searches:{timestamp}:stocksnap") == b"1"
    assert redis.get(f"provider_appeared_in_searches:{timestamp}:inaturalist") == b"1"
